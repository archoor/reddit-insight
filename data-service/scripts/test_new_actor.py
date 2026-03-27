"""
测试 fatihtahta/reddit-scraper-search-fast 的返回结构，
看它是否能同时返回帖子和评论。
使用方式：uv run python scripts/test_new_actor.py
"""
import sys, json
from pathlib import Path
from collections import Counter
sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")
from apify_client import ApifyClient
from app.config import settings

client = ApifyClient(settings.APIFY_API_TOKEN)

ACTOR_ID = "fatihtahta/reddit-scraper-search-fast"

# ─── 检查 Actor 是否存在 ────────────────────────────────
print("=== Actor 元数据 ===")
try:
    info = client.actor(ACTOR_ID).get()
    print(f"id:       {info.get('id')}")
    print(f"name:     {info.get('name')}")
    print(f"username: {info.get('username')}")
except Exception as e:
    print(f"[FAIL] {type(e).__name__}: {e}")
    sys.exit(1)

# ─── 测试1：采集 r/SaaS 帖子（小量） ───────────────────
print("\n=== Test 1: 采集 r/SaaS hot 帖子 (limit=3) ===")
try:
    run = client.actor(ACTOR_ID).call(
        run_input={
            "searches": [{"subreddit": "SaaS", "sort": "hot"}],
            "maxItems": 3,
            "proxy": {"useApifyProxy": True},
        },
        timeout_secs=120,
    )
    print(f"Status: {run.get('status')}")
    items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
    print(f"Total items: {len(items)}")
    dtypes = Counter(it.get("dataType") or it.get("type") or it.get("kind") or "?" for it in items)
    print(f"Types: {dict(dtypes)}")
    if items:
        first = items[0]
        print(f"\n--- First item keys ---")
        print(f"  {list(first.keys())}")
        print(f"  dataType: {first.get('dataType')}")
        print(f"  title:    {(first.get('title') or '')[:80]}")
        print(f"  url:      {first.get('url') or first.get('link')}")
        print(f"  score:    {first.get('score')}")
        print(f"  id:       {first.get('id')}")
        print(f"  author:   {first.get('author') or first.get('username')}")
        print(f"  subreddit:{first.get('subreddit') or first.get('communityName')}")
        print(f"  created:  {first.get('createdAt') or first.get('created_utc')}")
        print(f"  numComments: {first.get('numComments') or first.get('num_comments')}")
        # 是否有评论字段？
        comment_fields = [k for k in first.keys() if 'comment' in k.lower()]
        print(f"  comment-related fields: {comment_fields}")
        print(f"\n  Full item (truncated):")
        for k, v in first.items():
            print(f"    {k}: {str(v)[:100]}")
except Exception as e:
    print(f"[FAIL] {type(e).__name__}: {e}")
    import traceback; traceback.print_exc()

# ─── 测试2：通过 URL 采集特定帖子（看是否有评论） ────────
print("\n=== Test 2: 通过 URL 采集特定帖子 (检测评论) ===")
try:
    run = client.actor(ACTOR_ID).call(
        run_input={
            "startUrls": [{"url": "https://www.reddit.com/r/SaaS/comments/1s4hwj0/everything_in_our_stack_works_but_together_its/"}],
            "maxItems": 100,
            "proxy": {"useApifyProxy": True},
        },
        timeout_secs=120,
    )
    print(f"Status: {run.get('status')}")
    items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
    print(f"Total items: {len(items)}")
    dtypes = Counter(it.get("dataType") or it.get("type") or it.get("kind") or "?" for it in items)
    print(f"Types: {dict(dtypes)}")
    for i, item in enumerate(items[:5]):
        dt = item.get("dataType") or item.get("type") or "?"
        body = (item.get("body") or item.get("text") or item.get("selftext") or "")[:80]
        title = (item.get("title") or "")[:50]
        print(f"  [{i}] {dt} | title={title} | body={body}")
except Exception as e:
    print(f"[FAIL] {type(e).__name__}: {e}")

print("\nDone.")
