"""
商机评估引擎：从 PostAnalysis 中的 opportunities_raw 数组批量生成 Opportunity 记录。

核心改变（vs 旧版）：
  1. 一帖可产出 1~5 条 Opportunity（由 LLM 决定）
  2. 通过 post_id + opportunity_index 联合去重，支持重新分析时正确更新
  3. 修复了旧版 generate_subreddit_report 中的自关联 JOIN bug
"""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from slugify import slugify
from sqlmodel import Session, select, func

from app.config import settings
from app.models.opportunity import Opportunity
from app.models.post_analysis import PostAnalysis
from app.models.post import Post

logger = logging.getLogger(__name__)


def _make_slug(title: str, subreddit: str, post_id: int, index: int) -> str:
    """
    生成唯一的 SEO slug。
    格式：{slugify(title)}-{subreddit}-{post_id}-{index}
    index 用于区分同一帖子内的多个商机。
    """
    base = slugify(title, max_length=60, word_boundary=True) or "opportunity"
    return f"{base}-{subreddit}-{post_id}-{index}"


def generate_opportunities_from_analysis(
    session: Session,
    analysis: PostAnalysis,
    post: Any,
    opportunities_data: List[Dict[str, Any]],
) -> List[Opportunity]:
    """
    从 LLM 返回的 opportunities[] 数组批量生成 Opportunity 记录。
    只为 opportunity_score >= THRESHOLD 的商机创建记录。

    Args:
        session: 数据库会话
        analysis: PostAnalysis 记录
        post: Post 对象
        opportunities_data: LLM 返回的商机数组（来自 opportunities_raw）

    Returns:
        生成的 Opportunity 记录列表
    """
    # 从分析结果的六维度数据中提取公共信息
    pain_points_data = analysis.pain_points or {}
    wtp_data = analysis.willingness_to_pay or {}
    competition_data = analysis.competition or {}
    ops_data = analysis.operational_risks or {}

    # 公共竞品列表（各商机共享）
    competitors_raw = competition_data.get("competitors_mentioned", [])
    all_competitor_names = [
        c.get("name", "") for c in competitors_raw if isinstance(c, dict)
    ]

    results: List[Opportunity] = []

    for index, opp_data in enumerate(opportunities_data):
        score = int(opp_data.get("opportunity_score", 0))
        if score < settings.OPPORTUNITY_SCORE_THRESHOLD:
            logger.debug(
                f"[opportunity_engine] 跳过商机 index={index} (score={score} < threshold={settings.OPPORTUNITY_SCORE_THRESHOLD})"
            )
            continue

        title = (opp_data.get("title") or post.title)[:60].strip()
        if not title:
            title = f"Opportunity from r/{post.subreddit_name}"

        slug = _make_slug(title, post.subreddit_name, post.id, index)

        # 按 post_id + opportunity_index 查找已有记录（支持重新分析时更新）
        existing = session.exec(
            select(Opportunity).where(
                Opportunity.post_id == post.id,
                Opportunity.opportunity_index == index,
            )
        ).first()

        opp = existing or Opportunity(
            post_id=post.id,
            post_analysis_id=analysis.id,
            opportunity_index=index,
        )

        # 优先使用 LLM 在 opportunities[] 中返回的各维度分数，
        # 其次回退到分析结果的公共维度数据
        wtp_score = int(opp_data.get("willingness_to_pay_score", 0)) or int(wtp_data.get("score", 0))
        pain_intensity = int(opp_data.get("pain_point_intensity", 0))
        if not pain_intensity:
            pain_items = pain_points_data.get("items", [])
            pain_intensity = max((int(p.get("intensity", 0)) for p in pain_items), default=0)

        tech_difficulty = int(opp_data.get("tech_difficulty", 0))
        if not tech_difficulty:
            tech_feasibility_data = analysis.tech_feasibility or {}
            feasibility_score = int(tech_feasibility_data.get("feasibility_score", 5))
            tech_difficulty = max(1, min(10, 10 - feasibility_score + 1))

        sustainability = int(opp_data.get("sustainability_score", 0)) or int(ops_data.get("sustainability_score", 5))

        opp.post_analysis_id = analysis.id
        opp.title = title
        opp.slug = slug
        opp.subreddit_name = post.subreddit_name
        opp.description = opp_data.get("summary", "")
        opp.recommendation = opp_data.get("recommendation", "")
        opp.score = score
        opp.pain_point_intensity = pain_intensity
        opp.willingness_to_pay_score = wtp_score
        opp.tech_difficulty = tech_difficulty
        opp.sustainability_score = sustainability
        opp.market_size_estimate = opp_data.get("market_size_estimate", "")
        opp.target_audience = opp_data.get("target_audience", "")
        opp.monetization_model = opp_data.get("monetization_model", "")
        opp.key_features = opp_data.get("key_features", [])
        opp.competitors = all_competitor_names
        opp.differentiation = competition_data.get("market_gap", "")
        opp.risks = opp_data.get("risks", [])
        opp.source_post_ids = [post.id]
        opp.evidence_count = 1
        opp.updated_at = datetime.now(timezone.utc)

        session.add(opp)
        results.append(opp)

        logger.info(
            f"[opportunity_engine] 生成商机: '{title}'"
            f" (post_id={post.id}, index={index}, score={score})"
        )

    session.commit()
    for opp in results:
        session.refresh(opp)

    return results


def get_top_opportunities(
    session: Session,
    subreddit: Optional[str] = None,
    limit: int = 20,
    min_score: int = 0,
) -> List[Opportunity]:
    """获取高分商机列表，按综合评分降序。"""
    query = select(Opportunity).where(Opportunity.score >= min_score)
    if subreddit:
        query = query.where(Opportunity.subreddit_name == subreddit)
    query = query.order_by(Opportunity.score.desc()).limit(limit)
    return list(session.exec(query).all())


def generate_subreddit_report(
    session: Session,
    subreddit_name: str,
) -> Dict[str, Any]:
    """
    生成某个 Subreddit 的聚合洞见报告。

    Bug 修复：原版错误地将 PostAnalysis 自关联，现改为通过 Post 表正确 JOIN。
    """
    # 获取该版块的所有商机（已按评分排序）
    opportunities = session.exec(
        select(Opportunity)
        .where(Opportunity.subreddit_name == subreddit_name)
        .order_by(Opportunity.score.desc())
    ).all()

    # 通过 Post 表正确关联，获取该版块的分析统计
    analyses_stats = session.exec(
        select(
            func.count(PostAnalysis.id).label("total_analyses"),
            func.avg(PostAnalysis.max_opportunity_score).label("avg_score"),
            func.sum(PostAnalysis.tokens_used).label("total_tokens"),
        )
        .join(Post, PostAnalysis.post_id == Post.id)
        .where(Post.subreddit_name == subreddit_name)
    ).first()

    total_analyses = int(analyses_stats[0]) if analyses_stats and analyses_stats[0] else 0
    avg_score = float(analyses_stats[1]) if analyses_stats and analyses_stats[1] else 0.0
    total_tokens = int(analyses_stats[2]) if analyses_stats and analyses_stats[2] else 0

    top_opportunities = [
        {
            "id": o.id,
            "title": o.title,
            "slug": o.slug,
            "score": o.score,
            "recommendation": o.recommendation,
            "target_audience": o.target_audience,
            "monetization_model": o.monetization_model,
        }
        for o in opportunities[:10]
    ]

    return {
        "subreddit": subreddit_name,
        "total_opportunities": len(opportunities),
        "total_analyses": total_analyses,
        "avg_opportunity_score": round(avg_score, 1),
        "total_tokens_used": total_tokens,
        "top_opportunities": top_opportunities,
        "monetization_distribution": _count_distribution(
            [o.monetization_model for o in opportunities]
        ),
        "recommendation_distribution": _count_distribution(
            [o.recommendation for o in opportunities]
        ),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def _count_distribution(items: List[str]) -> Dict[str, int]:
    """统计列表中各值的出现次数，按频次降序。"""
    result: Dict[str, int] = {}
    for item in items:
        if item:
            result[item] = result.get(item, 0) + 1
    return dict(sorted(result.items(), key=lambda x: -x[1]))
