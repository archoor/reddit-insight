"""
Subreddit 数据模型：记录被监控的 Reddit 子版块及其独立的采集参数。
"""
from datetime import datetime, timezone
from typing import Optional, List, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from app.models.post import Post


class SubredditBase(SQLModel):
    name: str = Field(index=True, unique=True, description="版块名称，不含 r/ 前缀")
    display_name: str = Field(default="", description="展示名称")
    description: Optional[str] = Field(default=None, description="版块描述")
    subscribers: int = Field(default=0, description="订阅人数")
    is_active: bool = Field(default=True, description="是否启用采集")

    # ── 帖子采集参数（每频道独立配置，全局任务扫描时使用） ──────────────────
    sort_by: str = Field(default="hot", description="排序方式: hot/new/top/rising")
    time_filter: Optional[str] = Field(
        default=None,
        description="时间跨度(仅 sort=top 时有效): hour/day/week/month/year/all",
    )
    post_limit: int = Field(default=25, description="每次采集帖子数上限，1-100")

    # ── 评论采集参数 ───────────────────────────────────────────────────────────
    fetch_comments: bool = Field(default=True, description="是否采集评论")
    comment_min_score: int = Field(
        default=5, description="触发评论采集的帖子最低分（低于此分跳过）"
    )
    comment_min_count: int = Field(
        default=10, description="触发评论采集的最低评论数（低于此数跳过）"
    )
    comment_max_per_post: int = Field(
        default=200, description="每帖最多采集评论数"
    )


class Subreddit(SubredditBase, table=True):
    __tablename__ = "subreddit"

    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    posts: List["Post"] = Relationship(back_populates="subreddit")


class SubredditCreate(SubredditBase):
    pass


class SubredditUpdate(SQLModel):
    """用于 PATCH 接口的可选更新字段（不传则保持原值）。"""
    display_name: Optional[str] = None
    description: Optional[str] = None
    subscribers: Optional[int] = None
    is_active: Optional[bool] = None
    sort_by: Optional[str] = None
    time_filter: Optional[str] = None
    post_limit: Optional[int] = None
    fetch_comments: Optional[bool] = None
    comment_min_score: Optional[int] = None
    comment_min_count: Optional[int] = None
    comment_max_per_post: Optional[int] = None


class SubredditRead(SubredditBase):
    id: int
    created_at: datetime
    updated_at: datetime
