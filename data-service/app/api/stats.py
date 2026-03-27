"""
统计数据 API：提供系统整体数据概览。
"""
from fastapi import APIRouter, Depends
from sqlmodel import Session, select, func

from app.database import get_session
from app.models.post import Post, AnalysisStatus
from app.models.comment import Comment
from app.models.subreddit import Subreddit
from app.models.collect_task import CollectTask

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("/overview")
def get_overview(session: Session = Depends(get_session)):
    """系统数据概览：帖子总数、评论总数、分析状态分布等。"""
    total_posts = session.exec(select(func.count()).select_from(Post)).one()
    total_comments = session.exec(select(func.count()).select_from(Comment)).one()
    total_subreddits = session.exec(select(func.count()).select_from(Subreddit)).one()
    total_tasks = session.exec(select(func.count()).select_from(CollectTask)).one()

    # 按分析状态统计
    analysis_stats = {}
    for status in [AnalysisStatus.PENDING, AnalysisStatus.QUEUED,
                   AnalysisStatus.ANALYZING, AnalysisStatus.DONE,
                   AnalysisStatus.FAILED, AnalysisStatus.SKIPPED]:
        count = session.exec(
            select(func.count()).select_from(Post).where(Post.analysis_status == status)
        ).one()
        analysis_stats[status] = count

    # 按版块统计帖子数
    subreddit_stats = session.exec(
        select(Post.subreddit_name, func.count(Post.id))
        .group_by(Post.subreddit_name)
        .order_by(func.count(Post.id).desc())
        .limit(10)
    ).all()

    # 最近采集的 5 个帖子
    recent_posts = session.exec(
        select(Post).order_by(Post.collected_at.desc()).limit(5)
    ).all()

    return {
        "total_posts": total_posts,
        "total_comments": total_comments,
        "total_subreddits": total_subreddits,
        "total_tasks": total_tasks,
        "analysis_status_distribution": analysis_stats,
        "posts_by_subreddit": [
            {"subreddit": row[0], "count": row[1]} for row in subreddit_stats
        ],
        "recent_posts": [
            {
                "id": p.id,
                "title": p.title,
                "subreddit_name": p.subreddit_name,
                "score": p.score,
                "analysis_status": p.analysis_status,
                "collected_at": p.collected_at.isoformat(),
            }
            for p in recent_posts
        ],
    }
