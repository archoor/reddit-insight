"""
评论采集服务（备用）：对指定帖子调用 Reddit JSON API 抓取评论并写入数据库。

注意：主采集流程已改用 Apify fatihtahta/reddit-scraper-search-fast Actor，
评论通过 collector.store_actor_comments() 直接从 Actor 返回数据入库，
无需再发起单独的 Reddit HTTP 请求。

本模块作为备用工具保留，可对单篇帖子单独补采评论（需 Reddit 网络可达）。

策略：
- 使用 Reddit 官方 JSON API（无需认证）：
  GET https://www.reddit.com/r/{sub}/comments/{post_id}.json?raw_json=1&limit=500
- 递归展开 MoreComments 占位（最多 1 层）
- 最多采集条数由调用方传入，按 score 降序截断
"""
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
from sqlmodel import Session, select

from app.config import settings
from app.models.comment import Comment
from app.models.post import Post

logger = logging.getLogger(__name__)

# Reddit API 请求头（需要自定义 User-Agent，否则会被限速）
_HEADERS = {
    "User-Agent": "reddit-insight-bot/1.0 (by /u/reddit-insight)",
    "Accept": "application/json",
}
_TIMEOUT = 45

# Apify Proxy URL（用 API Token 作密码，走美国节点绕过封锁）
# 格式：http://auto:<token>@proxy.apify.com:8000
def _get_apify_proxy() -> Optional[str]:
    """返回 Apify HTTP Proxy URL（若 token 未配置则返回 None）。"""
    token = getattr(settings, "APIFY_API_TOKEN", None)
    if token:
        return f"http://auto:{token}@proxy.apify.com:8000"
    return None


def _normalize_body(s: Any) -> Optional[str]:
    if not s or not isinstance(s, str):
        return None
    s = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", s.strip())
    if s in ("[deleted]", "[removed]", ""):
        return None
    return s


def _parse_utc(value: Any) -> Optional[datetime]:
    if not value:
        return None
    try:
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value, tz=timezone.utc)
        if isinstance(value, str):
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        pass
    return None


def _extract_from_listing(children: List[Dict], results: List[Dict]) -> None:
    """
    递归遍历 Reddit 评论列表（type=="t1"）并追加到 results。
    遇到 MoreComments（kind=="more"）则直接跳过（避免额外 API 请求）。
    """
    for child in children:
        kind = child.get("kind", "")
        if kind == "more":
            continue  # 忽略 MoreComments 占位
        if kind != "t1":
            continue  # 只处理评论类型
        data = child.get("data") or {}
        body = _normalize_body(data.get("body"))
        if not body:
            continue

        results.append({
            "reddit_id": data.get("id") or "",
            "parent_reddit_id": data.get("parent_id") or None,
            "body": body,
            "author": data.get("author") or None,
            "score": int(data.get("score") or 0),
            "reddit_created_at": _parse_utc(data.get("created_utc")),
        })

        # 递归处理子评论
        replies = (data.get("replies") or {})
        if isinstance(replies, dict):
            sub_children = replies.get("data", {}).get("children", [])
            _extract_from_listing(sub_children, results)


def fetch_comments_via_reddit_api(
    post: Post,
    max_comments: int = 200,
) -> List[Dict[str, Any]]:
    """
    调用 Reddit JSON API 获取帖子的评论列表。

    Args:
        post: 目标帖子 ORM 对象（需要 reddit_id 和 subreddit_name 字段）。
        max_comments: 最多返回多少条评论（按 score 降序截断）。

    Returns:
        标准化的评论字典列表，按 score 降序排列。
    """
    reddit_id = post.reddit_id
    subreddit  = post.subreddit_name

    # Reddit JSON API：返回 [post_listing, comments_listing]
    url = (
        f"https://www.reddit.com/r/{subreddit}/comments/{reddit_id}.json"
        f"?raw_json=1&limit=500&depth=10"
    )
    logger.info(f"[comment_fetcher] Reddit API 评论: {url}")

    proxy_url = _get_apify_proxy()

    try:
        # httpx >= 0.23 使用 Client(proxy=url) 配置代理
        with httpx.Client(
            proxy=proxy_url,
            timeout=_TIMEOUT,
            follow_redirects=True,
        ) as client:
            resp = client.get(url, headers=_HEADERS)
        resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        raise RuntimeError(f"Reddit API HTTP {e.response.status_code}: {url}") from e
    except httpx.RequestError as e:
        raise RuntimeError(f"Reddit API 请求失败: {e}") from e

    data = resp.json()
    if not isinstance(data, list) or len(data) < 2:
        logger.warning(f"[comment_fetcher] Reddit API 返回格式异常: {type(data)}")
        return []

    comments_listing = data[1].get("data", {}).get("children", [])
    results: List[Dict[str, Any]] = []
    _extract_from_listing(comments_listing, results)

    # 按 score 降序并截断
    results.sort(key=lambda c: -c["score"])
    results = results[:max_comments]

    logger.info(f"[comment_fetcher] Reddit API 返回 {len(results)} 条评论 (reddit_id={reddit_id})")
    return results


def fetch_and_store_comments(
    session: Session,
    post: Post,
    max_comments_per_post: Optional[int] = None,
) -> int:
    """
    为指定帖子采集评论并写入数据库。

    Args:
        session: 数据库会话。
        post: 目标帖子 ORM 对象。
        max_comments_per_post: 最多采集评论数；None 则使用全局 settings 配置。

    Returns:
        本次新增的评论数。
    """
    _max = max_comments_per_post if max_comments_per_post is not None else settings.MAX_COMMENTS_PER_POST

    try:
        raw_comments = fetch_comments_via_reddit_api(post, max_comments=_max)
    except RuntimeError as e:
        err_str = str(e)
        # 网络不可达（Reddit 被屏蔽等）：记录错误后优雅退出，不中断整体任务
        if "10060" in err_str or "10054" in err_str or "请求失败" in err_str:
            logger.warning(
                f"[comment_fetcher] 帖子 {post.reddit_id} 评论采集被跳过（网络不可达）: {e}"
            )
            return 0
        logger.error(f"[comment_fetcher] 评论采集失败 (post={post.reddit_id}): {e}")
        raise

    inserted = 0
    for item in raw_comments:
        if not item.get("reddit_id"):
            continue
        # 幂等：已存在则跳过
        existing = session.exec(
            select(Comment).where(Comment.reddit_id == item["reddit_id"])
        ).first()
        if existing:
            continue

        # 判断层级：t3_ 前缀说明是直接回复帖子
        parent_id = item.get("parent_reddit_id") or ""
        depth = 0 if parent_id.startswith("t3_") else 1

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

    # 标记帖子评论已采集
    post.comments_fetched = True
    post.updated_at = datetime.now(timezone.utc)
    session.add(post)
    session.commit()

    logger.info(f"[comment_fetcher] 帖子 {post.reddit_id}: 新增 {inserted} 条评论")
    return inserted
