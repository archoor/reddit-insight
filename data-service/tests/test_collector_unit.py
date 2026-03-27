"""collector 模块中的纯函数单元测试（不访问 Apify）。"""
from datetime import datetime, timezone

import pytest

from app.services.collector import (
    _generate_slug,
    _normalize_body,
    _normalize_title,
    _parse_created_at,
)


# ── _normalize_title ───────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "raw,expected",
    [
        (None, "Untitled"),
        ("", "Untitled"),
        (123, "Untitled"),
        ("  Hello  ", "Hello"),
        ("a\x00b", "ab"),
    ],
)
def test_normalize_title(raw, expected):
    assert _normalize_title(raw) == expected


def test_normalize_title_truncates_long_string():
    long = "x" * 600
    assert len(_normalize_title(long)) == 500


# ── _normalize_body ────────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "raw,expected",
    [
        (None, None),
        ("", None),
        (456, None),
        ("  body  ", "body"),
        ("\x00", None),
    ],
)
def test_normalize_body(raw, expected):
    assert _normalize_body(raw) == expected


# ── _parse_created_at ──────────────────────────────────────────────────────────

def test_parse_created_at_iso_string():
    dt = _parse_created_at("2024-01-15T12:30:00Z")
    assert dt is not None
    assert dt.tzinfo is not None


def test_parse_created_at_timestamp():
    dt = _parse_created_at(1700000000.0)
    assert dt == datetime.fromtimestamp(1700000000.0, tz=timezone.utc)


def test_parse_created_at_invalid():
    assert _parse_created_at("not-a-date") is None


# ── _generate_slug ─────────────────────────────────────────────────────────────

def test_generate_slug_basic():
    slug = _generate_slug("My Post Title", "abc12")
    assert slug.endswith("-abc12")
    assert "my-post-title" in slug


def test_generate_slug_empty_title_uses_post():
    slug = _generate_slug("", "xyz99")
    assert slug == "post-xyz99"


# ── run_collection 参数透传：通过 monkeypatch 验证 time_filter 被传递 ─────────────

def test_run_collection_passes_time_filter(monkeypatch):
    """run_collection 应将 time_filter 透传给 fetch_posts_from_apify。"""
    captured = {}

    def fake_fetch(subreddits, limit=25, sort="hot", time_filter=None):
        captured["time_filter"] = time_filter
        return []

    def fake_upsert(session, items):
        return 0, 0

    monkeypatch.setattr("app.services.collector.fetch_posts_from_apify", fake_fetch)
    monkeypatch.setattr("app.services.collector.upsert_posts", fake_upsert)

    from app.services.collector import run_collection
    run_collection(
        session=None,
        subreddits=["tech"],
        sort="top",
        time_filter="week",
        fetch_comments=False,
    )
    assert captured["time_filter"] == "week"


def test_run_collection_comment_threshold_override(monkeypatch):
    """comment_min_score / comment_min_count / max_comments_per_post 覆盖值应被正确应用。"""
    from datetime import datetime, timezone
    from sqlmodel import Session, create_engine
    from sqlmodel import SQLModel

    # 使用内存 DB 做最小化集成
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    from app.models.post import Post
    from app.models.comment import Comment
    from app.models.subreddit import Subreddit
    SQLModel.metadata.create_all(engine)

    # 插入一条满足条件的帖子（score=100, num_comments=50）
    with Session(engine) as s:
        sub = Subreddit(name="t", display_name="t")
        s.add(sub)
        s.flush()
        s.add(Post(
            reddit_id="p1", subreddit_name="t", subreddit_id=sub.id,
            title="Test", score=100, num_comments=50,
            analysis_status="pending",
            reddit_created_at=datetime.now(timezone.utc),
        ))
        s.commit()

    fetch_calls = []

    def fake_fetch_comments(session, post, max_comments_per_post=None):
        fetch_calls.append(max_comments_per_post)
        return 0

    import app.services.collector as col_mod
    monkeypatch.setattr(col_mod, "fetch_posts_from_apify", lambda *a, **kw: [])
    monkeypatch.setattr(col_mod, "upsert_posts", lambda s, items: (0, 0))

    # 手动触发带阈值覆盖的 run_collection
    with Session(engine) as session:
        col_mod.run_collection(
            session=session,
            subreddits=["t"],
            fetch_comments=True,
            comment_min_score=1,   # 低阈值，p1 应满足
            comment_min_count=1,
            max_comments_per_post=77,
        )
