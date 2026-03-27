"""获取 fatihtahta/reddit-scraper-search-fast 的输入 schema。"""
import sys, json, httpx
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")
from app.config import settings

TOKEN = settings.APIFY_API_TOKEN
BASE  = "https://api.apify.com/v2"
AUTH  = {"Authorization": f"Bearer {TOKEN}"}

with httpx.Client(timeout=30) as c:
    # 版本1.3详情
    r = c.get(f"{BASE}/acts/TwqHBuZZPHJxiQrTU/versions/1.3", headers=AUTH)
    data = r.json().get("data", {})
    print("Keys:", list(data.keys()))
    
    schema = data.get("inputSchema")
    if schema:
        if isinstance(schema, str):
            schema = json.loads(schema)
        props = schema.get("properties", {})
        print("\n=== Input Properties ===")
        for k, v in props.items():
            typ = v.get("type", "?")
            default = v.get("default", "N/A")
            desc = str(v.get("description") or v.get("title") or "")[:100]
            print(f"  {k}: type={typ}, default={default}")
            if desc:
                print(f"     {desc}")
    else:
        print("No inputSchema in version data")
        print("gitRepoUrl:", data.get("gitRepoUrl"))
        print("tarballUrl:", data.get("tarballUrl"))
