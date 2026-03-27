"""
分析任务 API：触发 LLM 分析、查询分析结果和状态。

修复：
  1. 批量分析改用 ThreadPoolExecutor 控制并发（原版同时启动 N 个线程无上限）
  2. 去除 sys.path hack，直接导入同包模型
"""
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select, func

from app.database import engine, get_session
from app.models.post import Post, AnalysisStatus
from app.models.post_analysis import PostAnalysis, PostAnalysisRead
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/analysis", tags=["analysis"])

# 全局线程池，限制并发分析数量
_executor = ThreadPoolExecutor(max_workers=settings.ANALYSIS_MAX_WORKERS)


def _run_analysis(post_id: int, model: str) -> None:
    """在线程池中执行分析（避免阻塞 API 响应）。"""
    from app.services.analyzer import analyze_post

    with Session(engine) as session:
        try:
            analyze_post(session, post_id, model=model)
        except Exception as e:
            logger.error(f"[analysis_api] 分析失败 post_id={post_id}: {e}")


@router.post("/trigger/{post_id}", status_code=202)
def trigger_analysis(
    post_id: int,
    model: str = Query("", description="指定 LLM 模型（空字符串使用默认配置）"),
    session: Session = Depends(get_session),
):
    """触发对单篇帖子的 LLM 分析（异步后台执行）。"""
    post = session.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="帖子不存在")

    # 已有成功结果时提示使用 re-analyze
    existing = session.exec(
        select(PostAnalysis).where(PostAnalysis.post_id == post_id)
    ).first()
    if existing and not existing.error_message and existing.max_opportunity_score > 0:
        return {
            "message": "该帖子已有分析结果，若需重新分析请使用 re-analyze 接口",
            "post_id": post_id,
            "max_opportunity_score": existing.max_opportunity_score,
            "opportunities_count": existing.opportunities_count,
        }

    # 防止重复触发：已在分析中则跳过
    if post.analysis_status == AnalysisStatus.ANALYZING:
        return {"message": "该帖子正在分析中，请稍候", "post_id": post_id}

    _executor.submit(_run_analysis, post_id, model or settings.LLM_MODEL)
    return {
        "message": "分析任务已触发",
        "post_id": post_id,
        "model": model or settings.LLM_MODEL,
    }


@router.post("/re-analyze/{post_id}", status_code=202)
def re_analyze(
    post_id: int,
    model: str = Query("", description="指定 LLM 模型"),
    session: Session = Depends(get_session),
):
    """强制重新分析（覆盖已有结果，会重新生成商机记录）。"""
    post = session.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="帖子不存在")

    _executor.submit(_run_analysis, post_id, model or settings.LLM_MODEL)
    return {"message": "重新分析任务已触发", "post_id": post_id}


@router.post("/trigger-batch", status_code=202)
def trigger_batch_analysis(
    subreddit: Optional[str] = Query(None, description="限定版块，空则全局"),
    min_comments: int = Query(10, description="最低评论数门槛"),
    max_posts: int = Query(20, ge=1, le=100, description="本次批量分析的最大帖子数"),
    session: Session = Depends(get_session),
):
    """
    批量触发未分析的帖子（状态为 pending）。
    按帖子评分降序优先分析高质量帖子。
    使用线程池控制并发，不会同时启动过多 LLM 请求。
    """
    query = select(Post).where(
        Post.analysis_status == AnalysisStatus.PENDING,
        Post.num_comments >= min_comments,
    )
    if subreddit:
        query = query.where(Post.subreddit_name == subreddit)

    posts = session.exec(
        query.order_by(Post.score.desc()).limit(max_posts)
    ).all()

    for post in posts:
        _executor.submit(_run_analysis, post.id, settings.LLM_MODEL)

    return {
        "message": f"已触发 {len(posts)} 篇帖子的分析",
        "triggered": len(posts),
        "max_concurrent": settings.ANALYSIS_MAX_WORKERS,
    }


@router.get("/{post_id}", response_model=PostAnalysisRead)
def get_analysis(post_id: int, session: Session = Depends(get_session)):
    """获取帖子的分析结果（含原始多商机数组）。"""
    analysis = session.exec(
        select(PostAnalysis).where(PostAnalysis.post_id == post_id)
    ).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="该帖子尚无分析结果")
    return analysis


@router.get("", response_model=dict)
def list_analyses(
    min_score: int = Query(0, description="最低商机评分"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: Session = Depends(get_session),
):
    """获取所有分析结果列表，按最高商机评分降序。"""
    query = select(PostAnalysis).where(PostAnalysis.max_opportunity_score >= min_score)
    total = session.exec(select(func.count()).select_from(query.subquery())).one()
    items = session.exec(
        query.order_by(PostAnalysis.max_opportunity_score.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {"items": items, "total": total, "page": page, "page_size": page_size}
