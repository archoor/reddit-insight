import time

from sqlmodel import Session

from app.database import engine
from app.models.collect_task import CollectTask, TaskStatus
from app.models.subreddit import Subreddit


# ── 工具函数 ────────────────────────────────────────────────────────────────────

def _fake_run_collection(**kwargs):
    """模拟 run_collection，直接返回统计结果，不访问 Apify。"""
    return {"posts_inserted": 2, "posts_updated": 0, "comments_collected": 3}


def _create_active_sub(name: str = "mock_sub") -> int:
    """向数据库写入一个活跃 Subreddit，返回 id。"""
    with Session(engine) as s:
        sub = Subreddit(name=name, display_name=name, is_active=True)
        s.add(sub)
        s.commit()
        s.refresh(sub)
        return sub.id


def _wait_task_done(client, tid: int, timeout: float = 3.0) -> dict:
    """轮询直到任务状态不为 running，返回最终任务数据。"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        time.sleep(0.05)
        data = client.get(f"/api/tasks/{tid}").json()
        if data["status"] != TaskStatus.RUNNING:
            return data
    raise AssertionError(f"task {tid} did not finish in {timeout}s")


# ── 单频道任务 CRUD ─────────────────────────────────────────────────────────────

def test_create_list_get_task(client):
    r = client.post(
        "/api/tasks",
        json={
            "subreddit_name": "test",
            "sort_by": "hot",
            "post_limit": 5,
            "fetch_comments": False,
            "is_active": True,
        },
    )
    assert r.status_code == 201
    tid = r.json()["id"]

    r_list = client.get("/api/tasks")
    assert r_list.status_code == 200
    assert len(r_list.json()) == 1

    r_get = client.get(f"/api/tasks/{tid}")
    assert r_get.status_code == 200
    assert r_get.json()["subreddit_name"] == "test"


def test_create_task_with_time_filter(client):
    """创建带时间跨度和评论覆盖配置的单频道任务。"""
    r = client.post(
        "/api/tasks",
        json={
            "subreddit_name": "finance",
            "sort_by": "top",
            "time_filter": "week",
            "post_limit": 30,
            "fetch_comments": True,
            "comment_min_score": 15,
            "comment_min_count": 30,
            "max_comments_per_post": 150,
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert body["time_filter"] == "week"
    assert body["comment_min_score"] == 15
    assert body["max_comments_per_post"] == 150


def test_get_task_404(client):
    assert client.get("/api/tasks/99999").status_code == 404


# ── 单频道任务执行 ──────────────────────────────────────────────────────────────

def test_run_single_task_completes(client, monkeypatch):
    monkeypatch.setattr("app.services.collector.run_collection", _fake_run_collection)

    r = client.post(
        "/api/tasks",
        json={"subreddit_name": "mock", "sort_by": "new", "post_limit": 1, "fetch_comments": False},
    )
    tid = r.json()["id"]
    assert client.post(f"/api/tasks/{tid}/run").status_code == 202

    data = _wait_task_done(client, tid)
    assert data["status"] == TaskStatus.COMPLETED
    assert data["posts_collected"] == 2
    assert data["comments_collected"] == 3
    assert data["last_error"] is None


def test_run_task_passes_time_filter_and_comment_overrides(client, monkeypatch):
    """确认任务级参数被正确传递到 run_collection。"""
    captured = {}

    def fake_run(session, subreddits, limit, sort, fetch_comments,
                 time_filter=None, comment_min_score=None,
                 comment_min_count=None, max_comments_per_post=None, **kw):
        captured.update(
            subreddits=subreddits, sort=sort, time_filter=time_filter,
            comment_min_score=comment_min_score, max_comments_per_post=max_comments_per_post,
        )
        return {"posts_inserted": 0, "posts_updated": 0, "comments_collected": 0}

    monkeypatch.setattr("app.services.collector.run_collection", fake_run)

    r = client.post(
        "/api/tasks",
        json={
            "subreddit_name": "science",
            "sort_by": "top",
            "time_filter": "month",
            "post_limit": 10,
            "comment_min_score": 20,
            "max_comments_per_post": 50,
        },
    )
    tid = r.json()["id"]
    client.post(f"/api/tasks/{tid}/run")
    _wait_task_done(client, tid)

    assert captured["time_filter"] == "month"
    assert captured["comment_min_score"] == 20
    assert captured["max_comments_per_post"] == 50


def test_run_task_404(client):
    assert client.post("/api/tasks/99999/run").status_code == 404


def test_run_task_conflict_when_running(client, monkeypatch):
    monkeypatch.setattr("app.services.collector.run_collection", _fake_run_collection)
    r = client.post(
        "/api/tasks",
        json={"subreddit_name": "x", "sort_by": "hot", "post_limit": 1},
    )
    tid = r.json()["id"]
    with Session(engine) as s:
        t = s.get(CollectTask, tid)
        t.status = TaskStatus.RUNNING
        s.add(t)
        s.commit()
    assert client.post(f"/api/tasks/{tid}/run").status_code == 409


# ── 全局任务 ────────────────────────────────────────────────────────────────────

def test_create_global_task(client):
    """subreddit_name 为 null → 全局任务。"""
    r = client.post(
        "/api/tasks",
        json={"sort_by": "hot", "post_limit": 10, "fetch_comments": False},
    )
    assert r.status_code == 201
    assert r.json()["subreddit_name"] is None


def test_run_global_task_sweeps_active_subreddits(client, monkeypatch):
    """全局任务应调用 run_collection 为每个活跃频道一次。"""
    _create_active_sub("alpha")
    _create_active_sub("beta")
    # 添加一个停用频道，不应被扫描
    with Session(engine) as s:
        s.add(Subreddit(name="inactive", display_name="inactive", is_active=False))
        s.commit()

    calls = []

    def fake_run(session, subreddits, **kw):
        calls.append(subreddits[0])
        return {"posts_inserted": 1, "posts_updated": 0, "comments_collected": 0}

    monkeypatch.setattr("app.services.collector.run_collection", fake_run)

    r = client.post("/api/tasks", json={"sort_by": "hot", "post_limit": 5})
    tid = r.json()["id"]
    client.post(f"/api/tasks/{tid}/run")
    data = _wait_task_done(client, tid)

    assert data["status"] == TaskStatus.COMPLETED
    assert set(calls) == {"alpha", "beta"}      # inactive 不在其中
    assert data["posts_collected"] == 2         # 每频道 1 篇，共 2 篇


def test_run_global_task_uses_subreddit_defaults(client, monkeypatch):
    """全局任务未覆盖的参数应使用频道自身配置。"""
    with Session(engine) as s:
        s.add(Subreddit(
            name="custom_sub", display_name="Custom",
            is_active=True,
            sort_by="top", time_filter="week",
            post_limit=50, comment_max_per_post=123,
        ))
        s.commit()

    captured = {}

    def fake_run(session, subreddits, limit, sort, time_filter=None, max_comments_per_post=None, **kw):
        captured.update(limit=limit, sort=sort, time_filter=time_filter,
                        max_comments_per_post=max_comments_per_post)
        return {"posts_inserted": 0, "posts_updated": 0, "comments_collected": 0}

    monkeypatch.setattr("app.services.collector.run_collection", fake_run)

    # 全局任务不设置覆盖值（post_limit=0 / sort_by="" 触发回落至频道配置）
    r = client.post("/api/tasks", json={"sort_by": "", "post_limit": 0})
    tid = r.json()["id"]
    client.post(f"/api/tasks/{tid}/run")
    _wait_task_done(client, tid)

    assert captured["sort"] == "top"
    assert captured["time_filter"] == "week"
    assert captured["limit"] == 50
    assert captured["max_comments_per_post"] == 123


def test_run_global_task_no_active_subreddits_completes(client, monkeypatch):
    """没有活跃频道时，全局任务应直接完成，不报错。"""
    monkeypatch.setattr("app.services.collector.run_collection", _fake_run_collection)
    r = client.post("/api/tasks", json={"sort_by": "hot", "post_limit": 5})
    tid = r.json()["id"]
    client.post(f"/api/tasks/{tid}/run")
    data = _wait_task_done(client, tid)
    assert data["status"] == TaskStatus.COMPLETED


# ── Toggle / Delete ────────────────────────────────────────────────────────────

def test_toggle_task(client):
    r = client.post(
        "/api/tasks",
        json={"subreddit_name": "y", "sort_by": "hot", "post_limit": 1, "is_active": True},
    )
    tid = r.json()["id"]
    r2 = client.patch(f"/api/tasks/{tid}/toggle")
    assert r2.status_code == 200
    assert r2.json()["is_active"] is False


def test_delete_task(client):
    r = client.post(
        "/api/tasks",
        json={"subreddit_name": "z", "sort_by": "hot", "post_limit": 1},
    )
    tid = r.json()["id"]
    assert client.delete(f"/api/tasks/{tid}").status_code == 204
    assert client.get("/api/tasks").json() == []


def test_delete_running_task_409(client):
    r = client.post(
        "/api/tasks",
        json={"subreddit_name": "run", "sort_by": "hot", "post_limit": 1},
    )
    tid = r.json()["id"]
    with Session(engine) as s:
        t = s.get(CollectTask, tid)
        t.status = TaskStatus.RUNNING
        s.add(t)
        s.commit()
    assert client.delete(f"/api/tasks/{tid}").status_code == 409
