"""
PostAnalysis 模型：存储 LLM 对单篇帖子的多维度商业洞见分析结果。

一篇帖子对应一条 PostAnalysis，但可产出 1~N 条 Opportunity 记录。
"""
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from sqlmodel import SQLModel, Field, Column
from sqlalchemy import JSON


class AnalysisVersion:
    V1 = "v1"


class PostAnalysis(SQLModel, table=True):
    __tablename__ = "post_analysis"

    id: Optional[int] = Field(default=None, primary_key=True)
    post_id: int = Field(foreign_key="post.id", unique=True, index=True, description="关联的帖子 ID")

    # ── 六大分析维度（JSON）────────────────────────────────────────────────────
    pain_points: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSON),
        description="真实痛点分析：items[], top_pain_point"
    )
    willingness_to_pay: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSON),
        description="付费意愿评估：score, signals[], price_sensitivity"
    )
    tech_feasibility: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSON),
        description="技术可行性：feasibility_score, tech_stack[], key_challenges[]"
    )
    competition: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSON),
        description="竞品分析：competitors_mentioned[], market_gap"
    )
    operational_risks: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSON),
        description="运营风险：sustainability_score, churn_risks[], moat_potential"
    )

    # ── 多商机结果（JSON 数组，最多5条）──────────────────────────────────────
    opportunities_raw: Optional[Any] = Field(
        default=None,
        sa_column=Column(JSON),
        description="LLM 返回的原始商机数组（opportunities[]），最多5条"
    )

    # ── 聚合字段（方便排序和展示）────────────────────────────────────────────
    max_opportunity_score: int = Field(default=0, index=True, description="该帖产出的最高商机评分 0-100")
    opportunities_count: int = Field(default=0, description="该帖产出的商机数量")

    # ── 元数据 ────────────────────────────────────────────────────────────────
    model_used: str = Field(default="", description="使用的 LLM 模型")
    analysis_version: str = Field(default=AnalysisVersion.V1)
    comments_total: int = Field(default=0, description="帖子实际评论总数")
    comments_sampled: int = Field(default=0, description="参与分析的采样评论数")
    tokens_used: int = Field(default=0, description="本次分析消耗的 token 总数")
    error_message: Optional[str] = Field(default=None, description="分析失败时的错误信息")

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PostAnalysisRead(SQLModel):
    """分析结果读取响应模型。"""
    id: int
    post_id: int
    pain_points: Optional[Dict[str, Any]]
    willingness_to_pay: Optional[Dict[str, Any]]
    tech_feasibility: Optional[Dict[str, Any]]
    competition: Optional[Dict[str, Any]]
    operational_risks: Optional[Dict[str, Any]]
    opportunities_raw: Optional[Any]
    max_opportunity_score: int
    opportunities_count: int
    model_used: str
    comments_total: int
    comments_sampled: int
    tokens_used: int
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime
