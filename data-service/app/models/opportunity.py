"""
Opportunity 模型：代表从单篇帖子中提炼出的商业机会。

一篇帖子（PostAnalysis）可产出 1~5 条 Opportunity，
每条 Opportunity 通过 post_id 和 post_analysis_id 关联到来源帖子。
"""
from datetime import datetime, timezone
from typing import Any, List, Optional
from sqlmodel import SQLModel, Field, Column
from sqlalchemy import JSON


class Opportunity(SQLModel, table=True):
    __tablename__ = "opportunity"

    id: Optional[int] = Field(default=None, primary_key=True)

    # ── 来源关联 ──────────────────────────────────────────────────────────────
    post_id: int = Field(
        foreign_key="post.id",
        index=True,
        description="来源帖子 ID"
    )
    post_analysis_id: int = Field(
        foreign_key="post_analysis.id",
        index=True,
        description="关联的分析记录 ID"
    )
    # 同一篇帖子中的第几个商机（0-based），和 post_id 联合唯一
    opportunity_index: int = Field(default=0, description="帖子内商机序号（0-based）")

    # ── 基本信息 ──────────────────────────────────────────────────────────────
    title: str = Field(description="商机标题，简洁描述核心机会")
    slug: str = Field(index=True, unique=True, description="SEO 友好的 URL slug")
    subreddit_name: str = Field(index=True, description="来源版块")
    description: str = Field(default="", description="商机详细描述（2-3 句摘要）")
    recommendation: str = Field(default="", description="LLM 建议：Build / Validate / Skip")

    # ── 评分维度 ──────────────────────────────────────────────────────────────
    score: int = Field(default=0, index=True, description="商机综合评分 0-100")
    pain_point_intensity: int = Field(default=0, description="痛点强度 1-10")
    willingness_to_pay_score: int = Field(default=0, description="付费意愿评分 1-10")
    tech_difficulty: int = Field(default=5, description="技术难度 1-10（越低越容易实现）")
    sustainability_score: int = Field(default=0, description="长期可持续性 1-10")
    market_size_estimate: str = Field(default="", description="市场规模估算描述")

    # ── 商业细节 ──────────────────────────────────────────────────────────────
    target_audience: str = Field(default="", description="目标用户画像")
    monetization_model: str = Field(default="", description="建议的盈利模式")
    key_features: Optional[List[str]] = Field(
        default=None, sa_column=Column(JSON), description="核心 MVP 功能列表"
    )
    competitors: Optional[List[str]] = Field(
        default=None, sa_column=Column(JSON), description="已知竞品名称"
    )
    differentiation: Optional[str] = Field(default=None, description="差异化机会描述")
    risks: Optional[List[str]] = Field(
        default=None, sa_column=Column(JSON), description="主要风险列表"
    )

    # ── 来源追踪（为未来跨帖聚合预留）──────────────────────────────────────
    source_post_ids: Optional[List[int]] = Field(
        default=None, sa_column=Column(JSON), description="支撑该商机的帖子 ID 列表"
    )
    evidence_count: int = Field(default=1, description="支撑证据（帖子）数量")

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class OpportunityRead(SQLModel):
    """商机详情响应模型。"""
    id: int
    post_id: int
    post_analysis_id: int
    opportunity_index: int
    title: str
    slug: str
    subreddit_name: str
    description: str
    recommendation: str
    score: int
    pain_point_intensity: int
    willingness_to_pay_score: int
    tech_difficulty: int
    sustainability_score: int
    market_size_estimate: str
    target_audience: str
    monetization_model: str
    key_features: Optional[List[str]]
    competitors: Optional[List[str]]
    differentiation: Optional[str]
    risks: Optional[List[str]]
    source_post_ids: Optional[List[int]]
    evidence_count: int
    created_at: datetime
    updated_at: datetime


class OpportunityListItem(SQLModel):
    """商机列表轻量响应模型。"""
    id: int
    post_id: int
    title: str
    slug: str
    subreddit_name: str
    recommendation: str
    score: int
    pain_point_intensity: int
    willingness_to_pay_score: int
    tech_difficulty: int
    sustainability_score: int
    target_audience: str
    monetization_model: str
    evidence_count: int
    created_at: datetime
