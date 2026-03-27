"""
数据库迁移脚本 v2：合并 insight-service 功能所需的表结构变更。

处理内容：
  1. post_analysis 表：
     - 重命名旧字段 opportunity_score → max_opportunity_score（通过复制数据）
     - 重命名旧字段 summary（废弃，数据保留在 opportunities_raw）
     - 新增 opportunities_raw（JSON）、max_opportunity_score、opportunities_count
  2. opportunity 表：
     - 新增 post_id（FK）、post_analysis_id（FK）、opportunity_index
     - 新增 recommendation 字段
     - 新增 sustainability_score 字段
     - 填充存量数据（尝试从旧记录反推 post_id）

使用方式：
  cd data-service
  uv run python scripts/migrate_insight.py

注意：SQLite 不支持 RENAME COLUMN（3.25.0 以下），脚本会通过 ADD COLUMN + UPDATE 处理。
"""
import sqlite3
import json
import os
from pathlib import Path


def get_db_path() -> str:
    """从环境变量或 .env 文件获取数据库路径。"""
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

    path_str = db_url.replace("sqlite:///", "")
    path = Path(path_str)
    if not path.is_absolute():
        path = Path(__file__).parent.parent / path
    return str(path)


def get_columns(conn: sqlite3.Connection, table: str) -> set:
    """获取表的所有列名。"""
    try:
        cur = conn.execute(f"PRAGMA table_info({table})")
        return {row[1] for row in cur.fetchall()}
    except Exception:
        return set()


def table_exists(conn: sqlite3.Connection, table: str) -> bool:
    """检查表是否存在。"""
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
    )
    return cur.fetchone() is not None


def add_column_if_missing(conn: sqlite3.Connection, table: str, col: str, definition: str):
    """安全地添加列，已存在则跳过。"""
    if col not in get_columns(conn, table):
        sql = f"ALTER TABLE {table} ADD COLUMN {col} {definition}"
        conn.execute(sql)
        print(f"  [ADD] {table}.{col}")
    else:
        print(f"  [OK]  {table}.{col} already exists")


def migrate_post_analysis(conn: sqlite3.Connection):
    """
    迁移 post_analysis 表。
    核心：将旧的单商机字段体系迁移到新的多商机体系。
    """
    print("\n[1] 迁移 post_analysis 表 ...")

    if not table_exists(conn, "post_analysis"):
        print("  [SKIP] post_analysis 表不存在，将由服务启动时自动创建")
        return

    cols = get_columns(conn, "post_analysis")

    # 1-a. 新增 opportunities_raw（存 LLM 返回的商机数组）
    add_column_if_missing(conn, "post_analysis", "opportunities_raw", "TEXT")

    # 1-b. 新增 max_opportunity_score（从旧 opportunity_score 复制数据）
    add_column_if_missing(conn, "post_analysis", "max_opportunity_score", "INTEGER NOT NULL DEFAULT 0")
    if "opportunity_score" in cols and "max_opportunity_score" in get_columns(conn, "post_analysis"):
        conn.execute("""
            UPDATE post_analysis
            SET max_opportunity_score = opportunity_score
            WHERE max_opportunity_score = 0 AND opportunity_score > 0
        """)
        print("  [DATA] 从 opportunity_score 同步数据到 max_opportunity_score")

    # 1-c. 新增 opportunities_count
    add_column_if_missing(conn, "post_analysis", "opportunities_count", "INTEGER NOT NULL DEFAULT 0")

    # 1-d. 将旧的 opportunity_assessment（单商机 JSON）迁移到 opportunities_raw（数组格式）
    #      只处理 opportunities_raw 为空但 opportunity_assessment 有数据的行
    if "opportunity_assessment" in cols:
        rows = conn.execute("""
            SELECT id, opportunity_assessment, summary
            FROM post_analysis
            WHERE opportunities_raw IS NULL AND opportunity_assessment IS NOT NULL
        """).fetchall()

        migrated = 0
        for row_id, assessment_str, summary in rows:
            try:
                assessment = json.loads(assessment_str) if assessment_str else {}
                if not assessment:
                    continue

                # 将旧单商机数据封装为数组格式
                legacy_opp = {
                    "opportunity_score": assessment.get("opportunity_score", 0),
                    "title": assessment.get("title", ""),
                    "summary": assessment.get("summary", summary or ""),
                    "recommendation": assessment.get("recommendation", ""),
                    "target_audience": assessment.get("target_audience", ""),
                    "monetization_model": assessment.get("monetization_model", ""),
                    "market_size_estimate": assessment.get("market_size_estimate", ""),
                    "key_features": assessment.get("key_features", []),
                    "risks": assessment.get("risks", []),
                    "pain_point_refs": [],
                    "willingness_to_pay_score": 0,
                    "pain_point_intensity": 0,
                    "tech_difficulty": 5,
                    "sustainability_score": 5,
                    "_migrated_from_v1": True,
                }

                conn.execute(
                    "UPDATE post_analysis SET opportunities_raw = ?, opportunities_count = 1 WHERE id = ?",
                    (json.dumps([legacy_opp], ensure_ascii=False), row_id)
                )
                migrated += 1
            except Exception as e:
                print(f"  [WARN] 行 id={row_id} 迁移失败: {e}")

        if migrated:
            print(f"  [DATA] 将 {migrated} 条旧 opportunity_assessment 迁移到 opportunities_raw")


def migrate_opportunity(conn: sqlite3.Connection):
    """
    迁移 opportunity 表。
    核心：新增关联字段 post_id、post_analysis_id、opportunity_index 和 recommendation。
    """
    print("\n[2] 迁移 opportunity 表 ...")

    if not table_exists(conn, "opportunity"):
        print("  [SKIP] opportunity 表不存在，将由服务启动时自动创建")
        return

    # 新增关联字段
    add_column_if_missing(conn, "opportunity", "post_id", "INTEGER NOT NULL DEFAULT 0")
    add_column_if_missing(conn, "opportunity", "post_analysis_id", "INTEGER NOT NULL DEFAULT 0")
    add_column_if_missing(conn, "opportunity", "opportunity_index", "INTEGER NOT NULL DEFAULT 0")
    add_column_if_missing(conn, "opportunity", "recommendation", "TEXT NOT NULL DEFAULT ''")
    add_column_if_missing(conn, "opportunity", "sustainability_score", "INTEGER NOT NULL DEFAULT 0")

    # 尝试从 source_post_ids 填充 post_id（旧版已存的数据）
    rows = conn.execute(
        "SELECT id, source_post_ids FROM opportunity WHERE post_id = 0 AND source_post_ids IS NOT NULL"
    ).fetchall()

    updated = 0
    for row_id, source_ids_str in rows:
        try:
            source_ids = json.loads(source_ids_str) if source_ids_str else []
            if source_ids and isinstance(source_ids, list) and source_ids[0]:
                post_id = int(source_ids[0])
                # 查找对应的 post_analysis
                pa_row = conn.execute(
                    "SELECT id FROM post_analysis WHERE post_id = ?", (post_id,)
                ).fetchone()
                pa_id = pa_row[0] if pa_row else 0
                conn.execute(
                    "UPDATE opportunity SET post_id = ?, post_analysis_id = ? WHERE id = ?",
                    (post_id, pa_id, row_id)
                )
                updated += 1
        except Exception as e:
            print(f"  [WARN] opportunity id={row_id} 填充 post_id 失败: {e}")

    if updated:
        print(f"  [DATA] 为 {updated} 条旧商机记录填充了 post_id")

    # 将旧的 subreddit_name (index) 改为支持（旧表可能无此索引，忽略报错）
    try:
        conn.execute("CREATE INDEX IF NOT EXISTS idx_opportunity_post_id ON opportunity (post_id)")
        print("  [IDX] 创建 opportunity.post_id 索引")
    except Exception:
        pass


def main():
    db_path = get_db_path()
    print(f"数据库路径：{db_path}")

    if not Path(db_path).exists():
        print("[SKIP] 数据库文件不存在，迁移无需执行（服务启动时会自动建表）")
        return

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")

    try:
        migrate_post_analysis(conn)
        migrate_opportunity(conn)
        conn.commit()
        print("\n[DONE] 迁移完成！")
        print("\n提示：迁移完成后请重新启动 data-service，")
        print("      服务启动时会自动为新表补充缺失的列（通过 SQLModel.metadata.create_all）。")
    except Exception as e:
        conn.rollback()
        print(f"\n[ERROR] 迁移失败，已回滚: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
