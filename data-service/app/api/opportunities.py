"""
商机 API：查询商机列表和详情。

变化：
  - 新增 post_id 筛选参数（查询某帖的所有商机）
  - 详情响应增加 post 基础信息
  - 列表结果包含 recommendation 字段
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select, func

from app.database import get_session
from app.models.opportunity import Opportunity, OpportunityRead, OpportunityListItem
from app.models.post import Post
from app.services.opportunity_engine import get_top_opportunities

router = APIRouter(prefix="/api/opportunities", tags=["opportunities"])


@router.get("", response_model=dict)
def list_opportunities(
    subreddit: Optional[str] = Query(None, description="按版块筛选"),
    post_id: Optional[int] = Query(None, description="按来源帖子 ID 筛选"),
    min_score: int = Query(0, description="最低商机评分"),
    max_tech_difficulty: Optional[int] = Query(None, description="最高技术难度（1-10）"),
    recommendation: Optional[str] = Query(None, description="按建议筛选：Build / Validate / Skip"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: Session = Depends(get_session),
):
    """
    获取商机列表，支持多维度筛选。
    按商机综合评分降序排列。
    """
    query = select(Opportunity).where(Opportunity.score >= min_score)
    if subreddit:
        query = query.where(Opportunity.subreddit_name == subreddit)
    if post_id is not None:
        query = query.where(Opportunity.post_id == post_id)
    if max_tech_difficulty is not None:
        query = query.where(Opportunity.tech_difficulty <= max_tech_difficulty)
    if recommendation:
        query = query.where(Opportunity.recommendation == recommendation)

    total = session.exec(select(func.count()).select_from(query.subquery())).one()
    items = session.exec(
        query.order_by(Opportunity.score.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    list_items = [
        OpportunityListItem(
            id=o.id,
            post_id=o.post_id,
            title=o.title,
            slug=o.slug,
            subreddit_name=o.subreddit_name,
            recommendation=o.recommendation,
            score=o.score,
            pain_point_intensity=o.pain_point_intensity,
            willingness_to_pay_score=o.willingness_to_pay_score,
            tech_difficulty=o.tech_difficulty,
            sustainability_score=o.sustainability_score,
            target_audience=o.target_audience,
            monetization_model=o.monetization_model,
            evidence_count=o.evidence_count,
            created_at=o.created_at,
        )
        for o in items
    ]
    return {"items": list_items, "total": total, "page": page, "page_size": page_size}


@router.get("/top", response_model=List[OpportunityListItem])
def get_top(
    limit: int = Query(10, ge=1, le=50),
    subreddit: Optional[str] = Query(None),
    session: Session = Depends(get_session),
):
    """获取 Top N 商机（首页展示用）。"""
    opportunities = get_top_opportunities(session, subreddit=subreddit, limit=limit)
    return [
        OpportunityListItem(
            id=o.id,
            post_id=o.post_id,
            title=o.title,
            slug=o.slug,
            subreddit_name=o.subreddit_name,
            recommendation=o.recommendation,
            score=o.score,
            pain_point_intensity=o.pain_point_intensity,
            willingness_to_pay_score=o.willingness_to_pay_score,
            tech_difficulty=o.tech_difficulty,
            sustainability_score=o.sustainability_score,
            target_audience=o.target_audience,
            monetization_model=o.monetization_model,
            evidence_count=o.evidence_count,
            created_at=o.created_at,
        )
        for o in opportunities
    ]


@router.get("/{opportunity_id}", response_model=dict)
def get_opportunity(opportunity_id: int, session: Session = Depends(get_session)):
    """获取商机详情，附带来源帖子基础信息。"""
    opp = session.get(Opportunity, opportunity_id)
    if not opp:
        raise HTTPException(status_code=404, detail="商机不存在")

    # 附带来源帖子信息
    post = session.get(Post, opp.post_id)
    post_info = None
    if post:
        post_info = {
            "id": post.id,
            "title": post.title,
            "subreddit_name": post.subreddit_name,
            "score": post.score,
            "num_comments": post.num_comments,
            "url": post.url,
            "permalink": post.permalink,
            "reddit_created_at": post.reddit_created_at.isoformat() if post.reddit_created_at else None,
        }

    opp_dict = OpportunityRead.model_validate(opp).model_dump()
    opp_dict["source_post"] = post_info
    return opp_dict


@router.get("/by-slug/{slug}", response_model=dict)
def get_opportunity_by_slug(slug: str, session: Session = Depends(get_session)):
    """通过 slug 获取商机详情（SEO 页面用）。"""
    opp = session.exec(select(Opportunity).where(Opportunity.slug == slug)).first()
    if not opp:
        raise HTTPException(status_code=404, detail="商机不存在")

    post = session.get(Post, opp.post_id)
    post_info = None
    if post:
        post_info = {
            "id": post.id,
            "title": post.title,
            "subreddit_name": post.subreddit_name,
            "score": post.score,
            "num_comments": post.num_comments,
            "url": post.url,
            "permalink": post.permalink,
            "reddit_created_at": post.reddit_created_at.isoformat() if post.reddit_created_at else None,
        }

    opp_dict = OpportunityRead.model_validate(opp).model_dump()
    opp_dict["source_post"] = post_info
    return opp_dict
