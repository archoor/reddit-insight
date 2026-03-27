"""
Reddit 帖子+评论采集服务，基于 Apify fatihtahta/reddit-scraper-search-fast。

该 Actor 一次调用同时返回帖子（kind="post"）和评论（kind="comment"），
不再需要单独调用 Reddit API 采集评论，彻底解决了网络封锁问题。
"""
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from apify_client import ApifyClient
from slugify import slugify
from sqlmodel import Session, select

from app.config import settings
from app.models.post import Post, AnalysisStatus
from app.models.subreddit import Subreddit

logger = logging.getLogger(__name__)

ACTOR_ID = settings.APIFY_ACTOR_ID

# 新 Actor sort 选项白名单
_VALID_SUBREDDIT_SORTS = {"hot", "new", "top", "relevance", "comments"}
# 新 Actor timeframe 选项白名单
_VALID_TIMEFRAMES = {"hour", "day", "week", "month", "year", "all"}


def _normalize_title(s: Any) -> str:
    if not s or not isinstance(s, str):
        return "Untitled"
    s = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", s.strip())
    return s[:500]


def _normalize_body(s: Any) -> Optional[str]:
    if not s or not isinstance(s, str):
        return None
    s = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", s.strip())
    if s in ("[deleted]", "[removed]", ""):
        return None
    return s


def _parse_created_at(value: Any) -> Optional[datetime]:
    """解析 ISO 8601 或 Unix 时间戳 → datetime。"""
    if not value:
        return None
    try:
        if isinstance(value, str):
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value, tz=timezone.utc)
    except Exception:
        pass
    return None


def _generate_slug(title: str, reddit_id: str) -> str:
    base = slugify(title, max_length=80, word_boundary=True)
    if not base:
        base = "post"
    return f"{base}-{reddit_id}"


def _clean_subreddit_sort(sort: str) -> str:
    """将旧格式 sort（rising）映射为新 Actor 支持的 sort。"""
    # rising 不被新 Actor 支持，降级为 new
    if sort == "rising":
        return "new"
    return sort if sort in _VALID_SUBREDDIT_SORTS else "hot"


def _clean_timeframe(timeframe: Optional[str]) -> Optional[str]:
    if not timeframe:
        return None
    return timeframe if timeframe in _VALID_TIMEFRAMES else None


# ─── 从 Apify 采集帖子+评论 ──────────────────────────────


def fetch_posts_from_apify(
    subreddits: List[str],
    limit: int = 25,
    sort: str = "hot",
    time_filter: Optional[str] = None,
    fetch_comments: bool = False,
    max_comments_per_post: Optional[int] = None,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    调用 Apify fatihtahta/reddit-scraper-search-fast 采集帖子和评论。

    新 Actor 每次调用只接受一个 subredditName；如需多个版块，串行调用后合并。

    Args:
        subreddits: 目标版块名称列表（不含 r/ 前缀）。
        limit: 每个版块最多采集帖子数，最小为 10（Actor 限制）。
        sort: 排序方式：hot / new / top / relevance / comments。
        time_filter: 时间跨度：hour/day/week/month/year/all（top 排序时有效）。
        fetch_comments: 是否同步采集评论。
        max_comments_per_post: 每帖最多采集评论数。

    Returns:
        (posts_list, comments_list) 标准化字典列表对。
    """
    if not settings.APIFY_API_TOKEN:
        raise RuntimeError("APIFY_API_TOKEN 未配置，请在 .env 文件中设置。")

    client = ApifyClient(settings.APIFY_API_TOKEN)
    real_sort = _clean_subreddit_sort(sort)
    real_timeframe = _clean_timeframe(time_filter)
    real_limit = max(10, min(limit, 1000))  # Actor 要求 maxPosts >= 10
    _max_cmts = max_comments_per_post if max_comments_per_post is not None else settings.MAX_COMMENTS_PER_POST

    all_posts: List[Dict[str, Any]] = []
    all_comments: List[Dict[str, Any]] = []

    for subreddit in subreddits:
        run_input: Dict[str, Any] = {
            "subredditName": subreddit,
            "subredditSort": real_sort,
            "maxPosts": real_limit,
            "scrapeComments": fetch_comments,
            "maxComments": _max_cmts if fetch_comments else 10,
            "includeNsfw": False,
        }
        # 仅在 sort=top/relevance 时附加 timeframe
        if real_timeframe and real_sort in ("top", "relevance", "comments"):
            run_input["subredditTimeframe"] = real_timeframe

        logger.info(
            f"[collector] Apify Actor: subreddit={subreddit}, sort={real_sort}, "
            f"limit={real_limit}, fetch_comments={fetch_comments}, time_filter={real_timeframe}"
        )
        run = client.actor(ACTOR_ID).call(run_input=run_input)

        post_count = 0
        comment_count = 0
        for item in client.dataset(run["defaultDatasetId"]).iterate_items():
            kind = item.get("kind", "")
            if kind == "post":
                parsed = _parse_post_item(item, subreddit)
                if parsed:
                    all_posts.append(parsed)
                    post_count += 1
            elif kind == "comment" and fetch_comments:
                parsed = _parse_comment_item(item)
                if parsed:
                    all_comments.append(parsed)
                    comment_count += 1

        logger.info(
            f"[collector] r/{subreddit}: {post_count} 帖子, {comment_count} 条评论"
        )

    logger.info(
        f"[collector] 合计: {len(all_posts)} 帖子, {len(all_comments)} 条评论"
    )
    return all_posts, all_comments


def _parse_post_item(item: Dict[str, Any], fallback_subreddit: str) -> Optional[Dict[str, Any]]:
    """将 Actor 返回的 kind=post 条目标准化为数据库字段。"""
    raw_id = (item.get("id") or "").strip()
    if not raw_id:
        return None
    # Actor 返回的 id 已是短 id（无 t3_ 前缀），但防御性处理
    post_id = raw_id[3:] if raw_id.startswith("t3_") else raw_id

    community = (item.get("subreddit") or fallback_subreddit).strip()
    # Actor 有时返回 "r/SaaS" 形式
    if community.startswith("r/"):
        community = community[2:]

    post_url = (item.get("url") or "").strip() or None
    permalink = item.get("permalink") or f"/r/{community}/comments/{post_id}"

    return {
        "reddit_id": post_id,
        "subreddit_name": community,
        "title": _normalize_title(item.get("title")),
        "selftext": _normalize_body(item.get("body")),
        "author": (item.get("author") or "").strip() or None,
        "score": int(item.get("score") or 0),
        "upvote_ratio": float(item.get("upvote_ratio") or 0.0),
        "num_comments": int(item.get("num_comments") or 0),
        "url": post_url,
        "permalink": permalink,
        "is_nsfw": bool(item.get("over_18") or False),
        "reddit_created_at": _parse_created_at(item.get("created_utc")),
    }


def _parse_comment_item(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """将 Actor 返回的 kind=comment 条目标准化为数据库字段。"""
    raw_id = (item.get("id") or "").strip()
    if not raw_id:
        return None

    body = _normalize_body(item.get("body"))
    if not body:
        return None

    post_reddit_id = (item.get("postId") or "").strip()
    # postId 有时带 t3_ 前缀
    if post_reddit_id.startswith("t3_"):
        post_reddit_id = post_reddit_id[3:]

    parent_id = (item.get("parentId") or "").strip() or None

    return {
        "reddit_id": raw_id,
        "post_reddit_id": post_reddit_id,   # 用于之后关联 post.id
        "parent_reddit_id": parent_id,
        "body": body,
        "author": (item.get("author") or "").strip() or None,
        "score": int(item.get("score") or 0),
        "depth": int(item.get("depth") or 0),
        "reddit_created_at": _parse_created_at(item.get("created_utc")),
    }


# ─── 写入数据库 ───────────────────────────────────────────


def upsert_posts(session: Session, items: List[Dict[str, Any]]) -> Tuple[int, int]:
    """
    将采集到的帖子写入数据库，已存在则更新动态字段，新增则插入。
    Subreddit 名称匹配采用大小写不敏感方式，避免 "SaaS" vs "saas" 重复建表。

    Returns:
        (inserted, updated) 数量元组。
    """
    from sqlalchemy import func as sa_func

    inserted, updated = 0, 0
    for item in items:
        existing = session.exec(
            select(Post).where(Post.reddit_id == item["reddit_id"])
        ).first()

        if existing:
            existing.score = item["score"]
            existing.upvote_ratio = item["upvote_ratio"]
            existing.num_comments = item["num_comments"]
            existing.updated_at = datetime.now(timezone.utc)
            session.add(existing)
            updated += 1
        else:
            # 大小写不敏感查找 Subreddit 记录
            sub_name_lower = item["subreddit_name"].lower()
            subreddit = session.exec(
                select(Subreddit).where(sa_func.lower(Subreddit.name) == sub_name_lower)
            ).first()
            if not subreddit:
                subreddit = Subreddit(
                    name=item["subreddit_name"],
                    display_name=item["subreddit_name"],
                )
                session.add(subreddit)
                session.flush()

            slug = _generate_slug(item["title"], item["reddit_id"])
            post = Post(
                reddit_id=item["reddit_id"],
                subreddit_id=subreddit.id,
                subreddit_name=item["subreddit_name"],
                title=item["title"],
                selftext=item["selftext"],
                author=item["author"],
                score=item["score"],
                upvote_ratio=item["upvote_ratio"],
                num_comments=item["num_comments"],
                url=item["url"],
                permalink=item["permalink"],
                slug=slug,
                is_nsfw=item["is_nsfw"],
                reddit_created_at=item["reddit_created_at"],
                analysis_status=AnalysisStatus.PENDING,
            )
            session.add(post)
            inserted += 1

    session.commit()
    logger.info(f"[collector] 帖子入库完成: inserted={inserted}, updated={updated}")
    return inserted, updated


def store_actor_comments(
    session: Session,
    comment_items: List[Dict[str, Any]],
    comment_min_score: int = 0,
    comment_min_count: int = 0,
) -> int:
    """
    将 Actor 返回的评论批量写入数据库（幂等）。

    只存储其父帖子满足 min_score / min_count 条件的评论；
    同时将父帖子的 comments_fetched 标记为 True。

    Args:
        session: 数据库会话。
        comment_items: _parse_comment_item() 返回的字典列表。
        comment_min_score: 父帖子最低分（低于此值的帖子评论跳过）。
        comment_min_count: 父帖子最低评论数（低于此值的帖子评论跳过）。

    Returns:
        本次新增的评论数。
    """
    from app.models.comment import Comment

    if not comment_items:
        return 0

    # 预加载所有相关帖子（按 reddit_id 索引），减少查询次数
    post_ids_needed = {c["post_reddit_id"] for c in comment_items if c.get("post_reddit_id")}
    posts_map: Dict[str, Post] = {}
    for pid in post_ids_needed:
        post = session.exec(select(Post).where(Post.reddit_id == pid)).first()
        if post:
            posts_map[pid] = post

    inserted = 0
    marked_posts: set = set()  # 已标记 comments_fetched=True 的帖子 reddit_id

    for item in comment_items:
        post_rid = item.get("post_reddit_id", "")
        post = posts_map.get(post_rid)
        if not post:
            # 帖子未入库（理论上不应发生）
            continue

        # 阈值过滤：父帖子分数 / 评论数不达标则跳过
        if post.score < comment_min_score:
            continue
        if post.num_comments < comment_min_count:
            continue

        # 幂等：已存在则跳过
        existing = session.exec(
            select(Comment).where(Comment.reddit_id == item["reddit_id"])
        ).first()
        if existing:
            continue

        # 判断深度：parent 以 t3_ 开头 → 一级评论（depth=0）
        parent_id = item.get("parent_reddit_id") or ""
        depth = item.get("depth", 0)
        if depth == 0 and parent_id and not parent_id.startswith("t3_"):
            depth = 1

        comment = Comment(
            reddit_id=item["reddit_id"],
            post_id=post.id,
            parent_reddit_id=parent_id or None,
            body=item["body"],
            author=item["author"],
            score=item["score"],
            depth=depth,
            reddit_created_at=item["reddit_created_at"],
        )
        session.add(comment)
        inserted += 1

        # 标记父帖子评论已采集
        if post.reddit_id not in marked_posts:
            post.comments_fetched = True
            post.updated_at = datetime.now(timezone.utc)
            session.add(post)
            marked_posts.add(post.reddit_id)

    session.commit()
    logger.info(
        f"[collector] 评论入库完成: inserted={inserted}, "
        f"covered posts={len(marked_posts)}"
    )
    return inserted


# ─── 完整采集流程入口 ─────────────────────────────────────


def run_collection(
    session: Session,
    subreddits: List[str],
    limit: int = 25,
    sort: str = "hot",
    fetch_comments: bool = True,
    time_filter: Optional[str] = None,
    comment_min_score: Optional[int] = None,
    comment_min_count: Optional[int] = None,
    max_comments_per_post: Optional[int] = None,
) -> Dict[str, Any]:
    """
    完整的采集流程入口：一次 Apify 调用同时拉取帖子 + 评论 → 全部入库。

    Args:
        session: 数据库会话。
        subreddits: 目标版块名称列表。
        limit: 每个版块最多采集帖子数（最小 10）。
        sort: 排序方式。
        fetch_comments: 是否采集评论（直接通过 Actor 获取，无需额外 HTTP 请求）。
        time_filter: 时间跨度（top/relevance 排序时有效）。
        comment_min_score: 触发评论存储的父帖子最低分；None 则用全局配置。
        comment_min_count: 触发评论存储的最低评论数；None 则用全局配置。
        max_comments_per_post: 每帖最多采集评论数；None 则用全局配置。

    Returns:
        本次采集统计字典：posts_inserted / posts_updated / comments_collected / subreddits。
    """
    _min_score = comment_min_score if comment_min_score is not None else settings.COMMENT_FETCH_MIN_SCORE
    _min_count = comment_min_count if comment_min_count is not None else settings.COMMENT_FETCH_MIN_COMMENTS
    _max_cmts = max_comments_per_post if max_comments_per_post is not None else settings.MAX_COMMENTS_PER_POST

    posts_raw, comments_raw = fetch_posts_from_apify(
        subreddits=subreddits,
        limit=limit,
        sort=sort,
        time_filter=time_filter,
        fetch_comments=fetch_comments,
        max_comments_per_post=_max_cmts,
    )

    inserted, updated = upsert_posts(session, posts_raw)

    comments_collected = 0
    if fetch_comments and comments_raw:
        logger.info(
            f"[collector] Actor 返回 {len(comments_raw)} 条评论，"
            f"过滤条件: min_score={_min_score}, min_count={_min_count}"
        )
        comments_collected = store_actor_comments(
            session,
            comments_raw,
            comment_min_score=_min_score,
            comment_min_count=_min_count,
        )
    elif fetch_comments:
        logger.info("[collector] 评论采集已启用，但 Actor 未返回评论数据")

    return {
        "posts_inserted": inserted,
        "posts_updated": updated,
        "comments_collected": comments_collected,
        "subreddits": subreddits,
    }
