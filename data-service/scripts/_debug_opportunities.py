import sqlite3
from pathlib import Path

conn = sqlite3.connect(str(Path(__file__).parent.parent / "reddit_insight.db"))

print("=== post_analysis 记录 ===")
rows = conn.execute(
    "SELECT id, post_id, max_opportunity_score, opportunities_count, error_message FROM post_analysis"
).fetchall()
if not rows:
    print("  (空，无任何分析记录)")
for r in rows:
    print(f"  analysis_id={r[0]} post_id={r[1]} max_score={r[2]} count={r[3]} error={r[4]}")

print()
print("=== opportunity 记录 ===")
rows = conn.execute(
    "SELECT id, post_id, title, score, slug FROM opportunity"
).fetchall()
if not rows:
    print("  (空，无任何商机记录)")
for r in rows:
    print(f"  id={r[0]} post_id={r[1]} score={r[3]} title={r[2][:50]}")

print()
print("=== 已完成分析的帖子 ===")
rows = conn.execute(
    "SELECT id, title, analysis_status FROM post WHERE analysis_status='done'"
).fetchall()
if not rows:
    print("  (无 done 状态的帖子)")
for r in rows:
    print(f"  post_id={r[0]} status={r[2]} title={r[1][:50]}")

conn.close()
