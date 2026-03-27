from datetime import datetime, timezone


# ── 基础 CRUD ──────────────────────────────────────────────────────────────────

def test_create_and_list_subreddit(client):
    r = client.post(
        "/api/subreddits",
        json={"name": "SaaS", "display_name": "SaaS", "is_active": True},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["name"] == "SaaS"
    assert "id" in body
    # 默认采集参数应被写入
    assert body["sort_by"] == "hot"
    assert body["post_limit"] == 25
    assert body["fetch_comments"] is True
    assert body["comment_min_score"] == 5
    assert body["comment_max_per_post"] == 200

    r2 = client.get("/api/subreddits")
    assert r2.status_code == 200
    items = r2.json()
    assert len(items) == 1
    assert items[0]["name"] == "SaaS"


def test_create_subreddit_with_custom_collect_config(client):
    """创建时指定自定义采集参数。"""
    r = client.post(
        "/api/subreddits",
        json={
            "name": "startups",
            "display_name": "Startups",
            "sort_by": "top",
            "time_filter": "week",
            "post_limit": 50,
            "fetch_comments": True,
            "comment_min_score": 10,
            "comment_min_count": 20,
            "comment_max_per_post": 100,
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert body["sort_by"] == "top"
    assert body["time_filter"] == "week"
    assert body["post_limit"] == 50
    assert body["comment_max_per_post"] == 100


def test_create_duplicate_subreddit_409(client):
    client.post("/api/subreddits", json={"name": "dup", "display_name": "Dup"})
    r = client.post("/api/subreddits", json={"name": "dup", "display_name": "Dup2"})
    assert r.status_code == 409


# ── PATCH 更新 ─────────────────────────────────────────────────────────────────

def test_update_subreddit_collect_config(client):
    """PATCH 接口只更新传入的字段，其他字段保持不变。"""
    r = client.post(
        "/api/subreddits",
        json={"name": "saas2", "display_name": "SaaS2", "post_limit": 25},
    )
    sid = r.json()["id"]

    r2 = client.patch(
        f"/api/subreddits/{sid}",
        json={"sort_by": "top", "time_filter": "month", "post_limit": 100},
    )
    assert r2.status_code == 200
    body = r2.json()
    assert body["sort_by"] == "top"
    assert body["time_filter"] == "month"
    assert body["post_limit"] == 100
    # 未传的字段保持原值
    assert body["display_name"] == "SaaS2"
    assert body["comment_max_per_post"] == 200


def test_update_subreddit_comment_thresholds(client):
    r = client.post("/api/subreddits", json={"name": "tech", "display_name": "Tech"})
    sid = r.json()["id"]

    r2 = client.patch(
        f"/api/subreddits/{sid}",
        json={"comment_min_score": 20, "comment_min_count": 50, "comment_max_per_post": 300},
    )
    assert r2.status_code == 200
    body = r2.json()
    assert body["comment_min_score"] == 20
    assert body["comment_min_count"] == 50
    assert body["comment_max_per_post"] == 300


def test_update_subreddit_404(client):
    assert client.patch("/api/subreddits/99999", json={"sort_by": "new"}).status_code == 404


# ── Delete / Toggle ───────────────────────────────────────────────────────────

def test_delete_subreddit(client):
    r = client.post("/api/subreddits", json={"name": "todel", "display_name": "To Del"})
    sid = r.json()["id"]
    r2 = client.delete(f"/api/subreddits/{sid}")
    assert r2.status_code == 204
    assert client.get("/api/subreddits").json() == []


def test_delete_subreddit_404(client):
    assert client.delete("/api/subreddits/99999").status_code == 404


def test_toggle_subreddit(client):
    r = client.post(
        "/api/subreddits",
        json={"name": "toggleme", "display_name": "T", "is_active": True},
    )
    sid = r.json()["id"]
    r2 = client.patch(f"/api/subreddits/{sid}/toggle")
    assert r2.status_code == 200
    assert r2.json()["is_active"] is False


def test_toggle_subreddit_404(client):
    assert client.patch("/api/subreddits/99999/toggle").status_code == 404
