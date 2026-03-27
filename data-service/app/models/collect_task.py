"""
CollectTask 数据模型：管理数据采集任务的配置和状态。

subreddit_name 为 null 时表示"全局任务"：执行时自动扫描所有 is_active=True 的 Subreddit，
每个频道使用自身配置（可被任务级参数覆盖）。
"""
from datetime import datetime, timezone
from typing import Optional
from sqlmodel import SQLModel, Field


class TaskStatus:
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class CollectTaskBase(SQLModel):
    subreddit_name: Optional[str] = Field(
        default=None,
        description="目标版块名称；为 null 时表示全局任务（采集所有 is_active=True 的频道）",
    )
    sort_by: str = Field(default="hot", description="排序方式: hot/new/top/rising")

    # 时间跨度：仅 sort=top 时有效
    time_filter: Optional[str] = Field(
        default=None,
        description="时间跨度(仅 sort=top 时有效): hour/day/week/month/year/all",
    )

    post_limit: int = Field(default=25, description="每次采集帖子上限，1-100")
    fetch_comments: bool = Field(default=True, description="是否同步采集评论")

    # 评论采集覆盖配置（null = 继承 Subreddit 频道配置或全局 config）
    comment_min_score: Optional[int] = Field(
        default=None, description="触发评论采集的帖子最低分，为 null 则继承频道/全局配置"
    )
    comment_min_count: Optional[int] = Field(
        default=None, description="触发评论采集的最低评论数，为 null 则继承频道/全局配置"
    )
    max_comments_per_post: Optional[int] = Field(
        default=None, description="每帖最多采集评论数，为 null 则继承频道/全局配置"
    )

    cron_expression: Optional[str] = Field(
        default=None, description="定时 cron 表达式，如 0 */6 * * *；为空则仅手动触发"
    )
    is_active: bool = Field(default=True, description="是否启用定时调度")


class CollectTask(CollectTaskBase, table=True):
    __tablename__ = "collect_task"

    id: Optional[int] = Field(default=None, primary_key=True)
    status: str = Field(default=TaskStatus.PENDING, index=True)
    last_run_at: Optional[datetime] = Field(default=None)
    last_error: Optional[str] = Field(default=None, description="最近一次失败的错误信息")
    posts_collected: int = Field(default=0, description="累计采集帖子数")
    comments_collected: int = Field(default=0, description="累计采集评论数")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CollectTaskCreate(CollectTaskBase):
    pass


class CollectTaskRead(CollectTaskBase):
    id: int
    status: str
    last_run_at: Optional[datetime]
    last_error: Optional[str]
    posts_collected: int
    comments_collected: int
    created_at: datetime
    updated_at: datetime
