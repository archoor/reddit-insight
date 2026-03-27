"""重置帖子的 comments_fetched 标记，用于测试评论采集。"""
import sqlite3
from pathlib import Path

db_path = Path(__file__).parent.parent / "reddit_insight.db"
conn = sqlite3.connect(str(db_path))
n = conn.execute(
    "UPDATE post SET comments_fetched=0 WHERE LOWER(subreddit_name)='saas'"
).rowcount
conn.commit()
conn.close()
print(f"Reset {n} posts -> comments_fetched=False")
