"""
调试脚本：直接调用 Apify 采集单帖评论，打印原始 dataset 的字段结构。
用于确认 macrocosmos/reddit-scraper 的 URL 模式输出格式。

使用方式：uv run python scripts/debug_comments.py
"""
import json
import sys
from pathlib import Path

# 确保能导入 app 模块
sys.path.insert(0, str(Path(__file__).parent.parent))

# 从 .env 加载环境变量
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from app.config import settings
from apify_client import ApifyClient

# 测试用的 SaaS 帖子 permalink（取一篇有一定评论数的帖子）
POST_URL = "https://www.reddit.com/r/SaaS/comments/1s4hwj0/everything_in_our_stack_works_but_together_its/"

def main():
    print(f"Apify token: {settings.APIFY_API_TOKEN[:20]}...")
    print(f"Actor ID: {settings.APIFY_ACTOR_ID}")
    print(f"Post URL: {POST_URL}")
    print()

    client = ApifyClient(settings.APIFY_API_TOKEN)
    run_input = {
        "url": POST_URL,
        "proxyConfiguration": {"useApifyProxy": True},
    }

    print("Calling Apify actor...")
    run = client.actor(settings.APIFY_ACTOR_ID).call(run_input=run_input)
    print(f"Run ID: {run.get('id')}, Status: {run.get('status')}")
    print()

    items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
    print(f"Total items in dataset: {len(items)}")
    print()

    for i, item in enumerate(items):
        print(f"--- Item {i} ---")
        print(f"  Keys: {list(item.keys())}")
        print(f"  dataType: {item.get('dataType')}")
        print(f"  title: {str(item.get('title',''))[:80]}")
        print(f"  body: {str(item.get('body',''))[:80]}")
        print(f"  id: {item.get('id')}")
        # 如果有 comments 字段，打印其结构
        if "comments" in item:
            comments = item["comments"]
            print(f"  comments: [{len(comments)} items]")
            if comments:
                first_c = comments[0]
                print(f"    first comment keys: {list(first_c.keys())}")
                print(f"    first comment body: {str(first_c.get('body',''))[:80]}")
                print(f"    first comment score: {first_c.get('score')}")
        print()


if __name__ == "__main__":
    main()
