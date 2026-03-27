"""
帖子查询 API：支持分页、筛选、搜索。
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select, func

from app.database import get_session
from app.models.post import Post, PostRead, PostListItem
from app.models.comment import Comment, CommentRead

router = APIRouter(prefix="/api/posts", tags=["posts"])


@router.get("", response_model=dict)
def list_posts(
    subreddit: Optional[str] = Query(None, description="按版块筛选"),
    analysis_status: Optional[str] = Query(None, description="按分析状态筛选"),
    search: Optional[str] = Query(None, description="标题关键词搜索"),
    min_score: Optional[int] = Query(None, description="最低评分"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: Session = Depends(get_session),
):
    """
    获取帖子列表，支持多维度筛选和分页。
    返回格式: {items, total, page, page_size}
    """
    query = select(Post)

    if subreddit:
        query = query.where(Post.subreddit_name == subreddit)
    if analysis_status:
        query = query.where(Post.analysis_status == analysis_status)
    if search:
        query = query.where(Post.title.contains(search))
    if min_score is not None:
        query = query.where(Post.score >= min_score)

    # 总数
    count_query = select(func.count()).select_from(query.subquery())
    total = session.exec(count_query).one()

    # 分页
    offset = (page - 1) * page_size
    posts = session.exec(
        query.order_by(Post.collected_at.desc()).offset(offset).limit(page_size)
    ).all()

    items = [
        PostListItem(
            id=p.id,
            reddit_id=p.reddit_id,
            subreddit_name=p.subreddit_name,
            title=p.title,
            author=p.author,
            score=p.score,
            num_comments=p.num_comments,
            url=p.url,
            permalink=p.permalink,
            slug=p.slug,
            analysis_status=p.analysis_status,
            comments_fetched=p.comments_fetched,
            reddit_created_at=p.reddit_created_at,
            collected_at=p.collected_at,
        )
        for p in posts
    ]

    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/{post_id}", response_model=PostRead)
def get_post(post_id: int, session: Session = Depends(get_session)):
    """获取单个帖子详情。"""
    post = session.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="帖子不存在")
    return post


@router.get("/{post_id}/comments", response_model=List[CommentRead])
def get_post_comments(
    post_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    sampled_only: bool = Query(False, description="只返回被采样用于分析的评论"),
    session: Session = Depends(get_session),
):
    """获取帖子的评论列表，按评分降序。"""
    post = session.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="帖子不存在")

    query = select(Comment).where(Comment.post_id == post_id)
    if sampled_only:
        query = query.where(Comment.is_sampled == True)

    offset = (page - 1) * page_size
    comments = session.exec(
        query.order_by(Comment.score.desc()).offset(offset).limit(page_size)
    ).all()
    return comments


@router.post("/{post_id}/fetch-comments", status_code=202)
def trigger_comment_fetch(post_id: int, session: Session = Depends(get_session)):
    """手动触发单帖评论采集（异步执行）。"""
    post = session.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="帖子不存在")

    import threading
    from app.services.comment_fetcher import fetch_and_store_comments
    from app.database import engine
    from sqlmodel import Session as S

    def _run():
        with S(engine) as s:
            p = s.get(Post, post_id)
            if p:
                fetch_and_store_comments(s, p)

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

    return {"message": "评论采集任务已触发", "post_id": post_id}
