"""
端到端冒烟测试脚本
===================
执行以下流程：
  1. 健康检查
  2. 添加 SaaS 频道（已存在则复用）
  3. 创建 24 小时定时监测任务（cron: 0 0 * * *）
  4. 手动触发一次采集
  5. 等待任务完成（最长 300s）
  6. 验证采集结果（帖子数 / 评论数 / stats）

使用方式：
    uv run python scripts/e2e_test.py
"""

import sys
import time
import json
import urllib.request
import urllib.error
import urllib.parse

BASE = "http://localhost:8001"
TIMEOUT = 10        # 单次请求超时（秒）
POLL_INTERVAL = 5   # 轮询间隔（秒）
POLL_MAX = 300       # 最长等待采集完成（秒）

# ─── HTTP 工具 ────────────────────────────────────────────────────────────────

def _request(method: str, path: str, body: dict | None = None) -> dict:
    url = BASE + path
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(
        url, data=data, method=method,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body_text = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code} {method} {path}: {body_text}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Cannot reach {url}: {e.reason}") from e


def GET(path):   return _request("GET",    path)
def POST(path, body=None): return _request("POST",   path, body)
def PATCH(path, body=None): return _request("PATCH",  path, body)


def ok(step: str, detail: str = ""):
    msg = f"  [PASS] {step}"
    if detail:
        msg += f"  =>  {detail}"
    print(msg)


def fail(step: str, detail: str = ""):
    print(f"  [FAIL] {step}  =>  {detail}")
    sys.exit(1)


def section(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


# ─── 测试步骤 ─────────────────────────────────────────────────────────────────

def step1_health():
    section("Step 1 / 健康检查")
    try:
        resp = GET("/health")
        assert resp.get("status") == "ok", f"unexpected: {resp}"
        ok("Health check", f"service={resp.get('service')}")
    except Exception as e:
        fail("Health check", str(e))


def step2_add_subreddit() -> int:
    """添加或复用 SaaS 频道，返回 subreddit_id。"""
    section("Step 2 / 添加 SaaS 频道")
    subreddits = GET("/api/subreddits")
    existing = next((s for s in subreddits if s["name"].lower() == "saas"), None)

    if existing:
        sub_id = existing["id"]
        ok("Subreddit already exists, reusing", f"id={sub_id}, is_active={existing['is_active']}")
        # 若被禁用则重新启用
        if not existing["is_active"]:
            updated = PATCH(f"/api/subreddits/{sub_id}/toggle")
            ok("Re-activated subreddit", f"is_active={updated['is_active']}")
        return sub_id

    body = {
        "name": "SaaS",
        "display_name": "SaaS",
        "sort_by": "hot",
        "post_limit": 10,          # 测试时采集 10 条够用
        "fetch_comments": True,
        "comment_min_score": 3,
        "comment_min_count": 5,
        "comment_max_per_post": 50,
    }
    resp = POST("/api/subreddits", body)
    sub_id = resp["id"]
    ok("Subreddit created", f"id={sub_id}, name={resp['name']}")
    return sub_id


def step3_create_task(subreddit_name: str = "SaaS") -> int:
    """创建 24h 定时任务，已存在则复用，返回 task_id。"""
    section("Step 3 / 创建 24h 定时监测任务")
    tasks = GET("/api/tasks")
    existing = next(
        (t for t in tasks if t.get("subreddit_name") == subreddit_name and t.get("cron_expression") == "0 0 * * *"),
        None,
    )
    if existing:
        task_id = existing["id"]
        ok("Task already exists, reusing", f"id={task_id}, status={existing['status']}")
        return task_id

    body = {
        "subreddit_name": subreddit_name,
        "sort_by": "hot",
        "post_limit": 10,
        "fetch_comments": True,
        "cron_expression": "0 0 * * *",   # 每天 00:00 执行
        "is_active": True,
    }
    resp = POST("/api/tasks", body)
    task_id = resp["id"]
    print(f"\n  任务详情：")
    print(f"    id              = {resp['id']}")
    print(f"    subreddit_name  = {resp['subreddit_name']}")
    print(f"    sort_by         = {resp['sort_by']}")
    print(f"    post_limit      = {resp['post_limit']}")
    print(f"    fetch_comments  = {resp['fetch_comments']}")
    print(f"    cron_expression = {resp['cron_expression']}")
    print(f"    is_active       = {resp['is_active']}")
    ok("Task created", f"id={task_id}")
    return task_id


def step4_run_task(task_id: int) -> dict:
    """触发任务，返回触发前的快照（用于对比增量）。"""
    section("Step 4 / 手动触发采集")
    # 记录触发前的基线（posts_collected 是累计值）
    baseline = GET(f"/api/tasks/{task_id}")
    baseline_posts    = baseline.get("posts_collected", 0)
    baseline_comments = baseline.get("comments_collected", 0)

    resp = POST(f"/api/tasks/{task_id}/run")
    ok("Task triggered", resp.get("message", ""))
    print(f"  => 基线：posts={baseline_posts}, comments={baseline_comments}")
    print(f"  => 正在等待任务完成（最长 {POLL_MAX}s）...")
    return {"baseline_posts": baseline_posts, "baseline_comments": baseline_comments}


def step5_wait_for_completion(task_id: int) -> dict:
    """
    等待当前轮次完成。
    策略：先等 status 变为 running，再等变为 completed/failed。
    避免因后台线程延迟而读到上次运行的旧状态。
    """
    section("Step 5 / 等待采集完成")
    deadline = time.time() + POLL_MAX

    # 阶段 1：等 running（最多等 30s，说明线程已启动）
    phase1_deadline = time.time() + 30
    while time.time() < phase1_deadline:
        task = GET(f"/api/tasks/{task_id}")
        status = task.get("status", "")
        print(f"  [{time.strftime('%H:%M:%S')}] waiting for running... status={status}", end="\r", flush=True)
        if status == "running":
            print(f"\n  [{time.strftime('%H:%M:%S')}] Task is now RUNNING")
            break
        time.sleep(1)
    else:
        # 30s 内没有变为 running；可能任务极快完成
        task = GET(f"/api/tasks/{task_id}")
        if task.get("status") == "completed":
            print(f"\n  [{time.strftime('%H:%M:%S')}] Task completed very fast (before polling caught running)")
        else:
            fail("Wait running", "Task did not enter running state within 30s")

    # 阶段 2：等 completed / failed
    while time.time() < deadline:
        task = GET(f"/api/tasks/{task_id}")
        status = task.get("status", "")
        print(f"  [{time.strftime('%H:%M:%S')}] status={status}  "
              f"posts={task.get('posts_collected',0)}  "
              f"comments={task.get('comments_collected',0)}", end="\r", flush=True)

        if status == "completed":
            print()
            ok("Task completed",
               f"posts_collected={task['posts_collected']}, comments_collected={task['comments_collected']}")
            return task
        if status == "failed":
            print()
            fail("Task failed", task.get("last_error", "unknown"))

        time.sleep(POLL_INTERVAL)

    print()
    fail("Timeout", f"Task {task_id} did not complete within {POLL_MAX}s")
    return {}  # unreachable


def step6_verify(task: dict, baseline: dict):
    section("Step 6 / 验证采集结果")

    posts_collected = task.get("posts_collected", 0)
    comments_collected = task.get("comments_collected", 0)
    delta_posts    = posts_collected    - baseline.get("baseline_posts", 0)
    delta_comments = comments_collected - baseline.get("baseline_comments", 0)

    print(f"  本轮增量：posts +{delta_posts}, comments +{delta_comments}")
    print(f"  累计总量：posts={posts_collected}, comments={comments_collected}")

    # 帖子：累计必须 > 0（首轮新增 > 0，后续也可以是 updated=n 则 delta=0）
    if posts_collected > 0:
        ok("Posts collected (cumulative)", f"{posts_collected} posts total")
    else:
        fail("Posts collected", "expected > 0 posts")

    # 查询帖子列表（先不带过滤，再尝试 saas/SaaS 大小写）
    posts_resp = GET("/api/posts?page=1&page_size=5")
    items = posts_resp.get("items", [])
    # 只保留 SaaS 相关的帖子（大小写不敏感）
    items = [i for i in items if i.get("subreddit_name", "").lower() == "saas"]
    total = posts_resp.get("total", 0)
    ok("Posts API", f"total_in_db={total}, saas_posts_shown={len(items)}")

    if items:
        p = items[0]
        print(f"\n  最新帖子：")
        print(f"    title          = {p['title'][:80]}")
        print(f"    score          = {p['score']}")
        print(f"    num_comments   = {p['num_comments']}")
        print(f"    analysis_status= {p['analysis_status']}")
        print(f"    comments_fetched={p.get('comments_fetched', 'N/A')}")

    # 全局 stats
    stats = GET("/api/stats/overview")
    print(f"\n  全局统计：")
    print(f"    total_posts       = {stats.get('total_posts', 0)}")
    print(f"    total_comments    = {stats.get('total_comments', 0)}")
    print(f"    total_subreddits  = {stats.get('total_subreddits', 0)}")
    print(f"    total_tasks       = {stats.get('total_tasks', 0)}")
    ok("Stats API", "OK")

    # 评论检查（若有评论）
    if comments_collected > 0:
        ok("Comments collected", f"{comments_collected} comments")
    elif delta_comments > 0:
        ok("Comments collected (this run)", f"+{delta_comments} comments")
    else:
        print("  [NOTE] No new comments collected")
        print("         Reason: posts may not meet comment_min_score/comment_min_count thresholds")
        print("         Or: comments already fetched in a previous run")


# ─── 主入口 ───────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  Reddit Insight - Data Service E2E Test")
    print(f"  Target: {BASE}")
    print("=" * 60)

    step1_health()
    sub_id = step2_add_subreddit()
    task_id = step3_create_task("SaaS")
    baseline = step4_run_task(task_id)
    task = step5_wait_for_completion(task_id)
    step6_verify(task, baseline)

    print("\n" + "=" * 60)
    print("  ALL STEPS PASSED")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
