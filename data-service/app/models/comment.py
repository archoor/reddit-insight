"""
Comment 数据模型：存储 Reddit 评论原始数据。
"""
from datetime import datetime, timezone
from typing import Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from app.models.post import Post


class CommentBase(SQLModel):
    reddit_id: str = Field(index=True, unique=True, description="评论唯一 ID，如 t1_xxx")
    post_id: int = Field(foreign_key="post.id", index=True)
    parent_reddit_id: Optional[str] = Field(default=None, description="父级 ID（t3_xxx 为一级评论）")
    body: str = Field(description="评论正文")
    author: Optional[str] = Field(default=None)
    score: int = Field(default=0, description="评论评分")
    depth: int = Field(default=0, description="评论层级深度，0=一级评论")
    is_sampled: bool = Field(default=False, description="是否被选入 LLM 分析样本")
    sample_reason: Optional[str] = Field(default=None, description="被采样的原因：top_score/long_text/top_level/controversial/random")
    reddit_created_at: Optional[datetime] = Field(default=None)


class Comment(CommentBase, table=True):
    __tablename__ = "comment"

    id: Optional[int] = Field(default=None, primary_key=True)
    collected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    post: Optional["Post"] = Relationship(back_populates="comments")


class CommentRead(CommentBase):
    id: int
    collected_at: datetime
