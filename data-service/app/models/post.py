"""
Post 数据模型：存储 Reddit 帖子原始数据。
"""
from datetime import datetime, timezone
from typing import Optional, List, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from app.models.subreddit import Subreddit
    from app.models.comment import Comment


class AnalysisStatus:
    PENDING = "pending"       # 待分析
    QUEUED = "queued"         # 已加入队列
    ANALYZING = "analyzing"   # 分析中
    DONE = "done"             # 分析完成
    FAILED = "failed"         # 分析失败
    SKIPPED = "skipped"       # 评论太少，跳过


class PostBase(SQLModel):
    reddit_id: str = Field(index=True, unique=True, description="Reddit 帖子唯一 ID，如 abc123")
    subreddit_name: str = Field(index=True, description="所属版块名称")
    title: str = Field(description="帖子标题")
    selftext: Optional[str] = Field(default=None, description="帖子正文")
    author: Optional[str] = Field(default=None, description="作者用户名")
    score: int = Field(default=0, description="帖子评分（赞踩差）")
    upvote_ratio: float = Field(default=0.0, description="点赞比例")
    num_comments: int = Field(default=0, description="评论总数（Reddit 端统计）")
    url: Optional[str] = Field(default=None, description="帖子原始链接")
    permalink: Optional[str] = Field(default=None, description="Reddit 站内永久链接")
    slug: Optional[str] = Field(default=None, index=True, description="SEO 友好的 URL slug")
    is_nsfw: bool = Field(default=False)
    reddit_created_at: Optional[datetime] = Field(default=None, description="帖子在 Reddit 的发布时间")
    comments_fetched: bool = Field(default=False, description="评论是否已采集")
    analysis_status: str = Field(default=AnalysisStatus.PENDING, index=True)


class Post(PostBase, table=True):
    __tablename__ = "post"

    id: Optional[int] = Field(default=None, primary_key=True)
    subreddit_id: Optional[int] = Field(default=None, foreign_key="subreddit.id", index=True)
    collected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    subreddit: Optional["Subreddit"] = Relationship(back_populates="posts")
    comments: List["Comment"] = Relationship(back_populates="post")


class PostRead(PostBase):
    id: int
    subreddit_id: Optional[int]
    collected_at: datetime
    updated_at: datetime
    comment_count_fetched: Optional[int] = None  # 实际采集到的评论数


class PostListItem(SQLModel):
    """帖子列表轻量响应。"""
    id: int
    reddit_id: str
    subreddit_name: str
    title: str
    author: Optional[str]
    score: int
    num_comments: int
    url: Optional[str]
    permalink: Optional[str]
    slug: Optional[str]
    analysis_status: str
    comments_fetched: bool
    reddit_created_at: Optional[datetime]
    collected_at: datetime
