"""
测试通过 Apify Proxy 调用 Reddit JSON API 获取评论。
使用方式：uv run python scripts/test_proxy_api.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

import httpx
from app.config import settings

POST_REDDIT_ID = "1s4hwj0"
SUBREDDIT = "SaaS"
URL = f"https://www.reddit.com/r/{SUBREDDIT}/comments/{POST_REDDIT_ID}.json?raw_json=1&limit=100&depth=5"

HEADERS = {
    "User-Agent": "reddit-insight-bot/1.0",
    "Accept": "application/json",
}

proxy_url = f"http://auto:{settings.APIFY_API_TOKEN}@proxy.apify.com:8000"
print(f"Proxy: {proxy_url[:40]}...")
print(f"URL: {URL}")
print()

try:
    with httpx.Client(proxy=proxy_url, timeout=45, follow_redirects=True) as client:
        resp = client.get(URL, headers=HEADERS)
    print(f"HTTP Status: {resp.status_code}")
    data = resp.json()
    print(f"Response type: {type(data)}, len: {len(data)}")

    if isinstance(data, list) and len(data) >= 2:
        post_listing   = data[0]["data"]["children"]
        comments_listing = data[1]["data"]["children"]
        print(f"Posts in listing: {len(post_listing)}")
        print(f"Comments in listing: {len(comments_listing)}")
        if comments_listing:
            c0 = comments_listing[0]
            print(f"First comment kind: {c0.get('kind')}")
            print(f"First comment score: {c0.get('data',{}).get('score')}")
            print(f"First comment body[:100]: {str(c0.get('data',{}).get('body',''))[:100]}")
    else:
        print("Unexpected response structure:", str(data)[:200])

except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
