"""查看 fatihtahta/reddit-scraper-search-fast 的输入 schema，了解正确参数。"""
import sys, json, httpx
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")
from apify_client import ApifyClient
from app.config import settings

TOKEN = settings.APIFY_API_TOKEN
BASE  = "https://api.apify.com/v2"
AUTH  = {"Authorization": f"Bearer {TOKEN}"}

client = ApifyClient(TOKEN)
ACTOR_ID = "fatihtahta/reddit-scraper-search-fast"

with httpx.Client(timeout=30) as c:
    # 获取 actor 详情
    r = c.get(f"{BASE}/acts/{ACTOR_ID}", headers=AUTH)
    data = r.json().get("data", {})
    print(f"id: {data.get('id')}")
    versions = data.get("versions") or []
    for v in versions:
        print(f"  version {v.get('versionNumber')}: sourceType={v.get('sourceType')}, buildTag={v.get('buildTag')}")
    
    # 获取最新版本
    if versions:
        latest_ver = versions[-1]["versionNumber"]
        r2 = c.get(f"{BASE}/acts/{data['id']}/versions/{latest_ver}", headers=AUTH)
        vdata = r2.json().get("data", {})
        print(f"\nLatest version {latest_ver} keys: {list(vdata.keys())}")
        
        # 获取 input schema
        inp_schema = vdata.get("inputSchema")
        if inp_schema:
            if isinstance(inp_schema, str):
                try:
                    inp_schema = json.loads(inp_schema)
                except:
                    pass
            if isinstance(inp_schema, dict):
                props = inp_schema.get("properties", {})
                print(f"\n=== Input Properties ===")
                for k, v in props.items():
                    typ = v.get("type", "")
                    default = v.get("default", "N/A")
                    desc = str(v.get("description") or v.get("title") or "")[:100]
                    print(f"  {k}: type={typ}, default={default} | {desc}")
            else:
                print(f"inputSchema: {str(inp_schema)[:500]}")
        else:
            print("No inputSchema")
    
    # 检查 prefill/example
    r3 = c.get(f"{BASE}/acts/{data['id']}/versions/{latest_ver}/input", headers=AUTH)
    print(f"\nInput endpoint: {r3.status_code} | {r3.text[:500]}")
