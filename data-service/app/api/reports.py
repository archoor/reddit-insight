"""
报告 API：聚合统计报告，为前端图表和 SEO 页面提供数据。

修复：generate_subreddit_report 中的自关联 JOIN bug 已在 opportunity_engine 中修复。
"""
from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select, func

from app.database import get_session
from app.models.post_analysis import PostAnalysis
from app.models.post import Post
from app.models.opportunity import Opportunity
from app.services.opportunity_engine import generate_subreddit_report

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/subreddit/{subreddit_name}")
def subreddit_report(subreddit_name: str, session: Session = Depends(get_session)):
    """获取特定 Subreddit 的聚合洞见报告。"""
    return generate_subreddit_report(session, subreddit_name)


@router.get("/overview")
def overview_report(session: Session = Depends(get_session)):
    """系统整体概览报告。"""
    total_analyses = session.exec(select(func.count()).select_from(PostAnalysis)).one()
    total_opportunities = session.exec(select(func.count()).select_from(Opportunity)).one()

    avg_score = session.exec(
        select(func.avg(PostAnalysis.max_opportunity_score))
    ).one() or 0

    # 高分商机（score >= 70）
    high_value = session.exec(
        select(func.count()).select_from(
            select(Opportunity).where(Opportunity.score >= 70).subquery()
        )
    ).one()

    # 按版块统计商机数（取前10）
    by_subreddit = session.exec(
        select(Opportunity.subreddit_name, func.count(Opportunity.id))
        .group_by(Opportunity.subreddit_name)
        .order_by(func.count(Opportunity.id).desc())
        .limit(10)
    ).all()

    # 按 recommendation 统计分布
    recommendation_dist = session.exec(
        select(Opportunity.recommendation, func.count(Opportunity.id))
        .group_by(Opportunity.recommendation)
    ).all()

    # Top 5 商机
    top_opportunities = session.exec(
        select(Opportunity).order_by(Opportunity.score.desc()).limit(5)
    ).all()

    # 总 token 消耗（成本参考）
    total_tokens = session.exec(
        select(func.sum(PostAnalysis.tokens_used))
    ).one() or 0

    return {
        "total_analyses": total_analyses,
        "total_opportunities": total_opportunities,
        "high_value_opportunities": high_value,
        "avg_opportunity_score": round(float(avg_score), 1),
        "total_tokens_used": int(total_tokens),
        "opportunities_by_subreddit": [
            {"subreddit": row[0], "count": row[1]} for row in by_subreddit
        ],
        "recommendation_distribution": {
            row[0]: row[1] for row in recommendation_dist if row[0]
        },
        "top_opportunities": [
            {
                "id": o.id,
                "title": o.title,
                "slug": o.slug,
                "score": o.score,
                "recommendation": o.recommendation,
                "subreddit_name": o.subreddit_name,
                "target_audience": o.target_audience,
            }
            for o in top_opportunities
        ],
    }
