"""
用正确参数测试 fatihtahta/reddit-scraper-search-fast。
正确输入：subredditName / subredditSort / maxPosts / scrapeComments / maxComments
使用方式：uv run python scripts/test_new_actor2.py
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

print("=== 测试：r/SaaS hot 帖子 + 评论（最多3帖、每帖5条评论）===")
try:
    run = client.actor(ACTOR_ID).call(
        run_input={
            "subredditName": "SaaS",
            "subredditSort": "hot",
            "maxPosts": 3,
            "scrapeComments": True,
            "maxComments": 5,
            "includeNsfw": False,
        },
        timeout_secs=300,
    )
    print(f"Status: {run.get('status')}")

    items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
    kind_counts = Counter(it.get("kind", "?") for it in items)
    print(f"Total items: {len(items)} | kinds: {dict(kind_counts)}")

    posts = [it for it in items if it.get("kind") == "post"]
    comments = [it for it in items if it.get("kind") == "comment"]

    print(f"\n=== Posts ({len(posts)}) ===")
    for p in posts[:3]:
        print(f"  id={p.get('id')} | score={p.get('score')} | subreddit={p.get('subreddit')}")
        print(f"  title={str(p.get('title',''))[:60]}")
        print(f"  created={p.get('created_utc')} | num_comments={p.get('num_comments')}")
        print(f"  author={p.get('author')} | url={str(p.get('url',''))[:60]}")
        print(f"  body={str(p.get('body',''))[:80]}")
        print(f"  keys: {list(p.keys())[:15]}")
        print()

    print(f"\n=== Comments ({len(comments)}) ===")
    for c in comments[:5]:
        print(f"  id={c.get('id')} | postId={c.get('postId')} | score={c.get('score')}")
        print(f"  author={c.get('author')} | depth={c.get('depth')}")
        print(f"  body={str(c.get('body',''))[:80]}")
        print(f"  keys: {list(c.keys())[:15]}")
        print()

except Exception as e:
    print(f"[FAIL] {type(e).__name__}: {e}")
    import traceback; traceback.print_exc()

print("Done.")
