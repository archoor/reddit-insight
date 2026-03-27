"""
数据库迁移脚本：为 collect_task 和 subreddit 表添加新字段。
使用方式：uv run python scripts/migrate_db.py
"""
import sqlite3
import os
from pathlib import Path

# 读取 DATABASE_URL，优先用环境变量，否则从 .env 读取
def get_db_path() -> str:
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        env_file = Path(__file__).parent.parent / ".env"
        if env_file.exists():
            for line in env_file.read_text(encoding="utf-8").splitlines():
                if line.startswith("DATABASE_URL="):
                    db_url = line.split("=", 1)[1].strip()
                    break
    if not db_url:
        db_url = "sqlite:///./reddit_insight.db"
    # 去掉 sqlite:/// 前缀，处理相对/绝对路径
    path_str = db_url.replace("sqlite:///", "")
    path = Path(path_str)
    if not path.is_absolute():
        path = Path(__file__).parent.parent / path
    return str(path)


# 列出某表的所有列名
def get_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    cur = conn.execute(f"PRAGMA table_info({table})")
    return {row[1] for row in cur.fetchall()}


# 安全地 ADD COLUMN（列已存在则跳过）
def add_column_if_missing(conn: sqlite3.Connection, table: str, col: str, definition: str):
    if col not in get_columns(conn, table):
        sql = f"ALTER TABLE {table} ADD COLUMN {col} {definition}"
        conn.execute(sql)
        print(f"  [ADD] {table}.{col}")
    else:
        print(f"  [OK]  {table}.{col} already exists")


def migrate(db_path: str):
    print(f"数据库路径：{db_path}")
    if not Path(db_path).exists():
        print("[SKIP] DB file not found, no migration needed (will be created on service start)")
        return

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")

    print("\n[1] 迁移 collect_task 表 ...")
    add_column_if_missing(conn, "collect_task", "time_filter",         "TEXT")
    add_column_if_missing(conn, "collect_task", "comment_min_score",    "INTEGER")
    add_column_if_missing(conn, "collect_task", "comment_min_count",    "INTEGER")
    add_column_if_missing(conn, "collect_task", "max_comments_per_post","INTEGER")

    print("\n[2] 迁移 subreddit 表 ...")
    add_column_if_missing(conn, "subreddit", "sort_by",              "TEXT NOT NULL DEFAULT 'hot'")
    add_column_if_missing(conn, "subreddit", "time_filter",          "TEXT")
    add_column_if_missing(conn, "subreddit", "post_limit",           "INTEGER NOT NULL DEFAULT 25")
    add_column_if_missing(conn, "subreddit", "fetch_comments",       "INTEGER NOT NULL DEFAULT 1")
    add_column_if_missing(conn, "subreddit", "comment_min_score",    "INTEGER NOT NULL DEFAULT 5")
    add_column_if_missing(conn, "subreddit", "comment_min_count",    "INTEGER NOT NULL DEFAULT 10")
    add_column_if_missing(conn, "subreddit", "comment_max_per_post", "INTEGER NOT NULL DEFAULT 200")

    conn.commit()
    conn.close()
    print("\n[DONE] Migration complete!")


if __name__ == "__main__":
    db_path = get_db_path()
    migrate(db_path)
