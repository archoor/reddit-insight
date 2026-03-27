"""导出所有模型，确保 SQLModel 元数据注册。"""
from app.models.subreddit import Subreddit, SubredditCreate, SubredditRead
from app.models.post import Post, PostRead, PostListItem, AnalysisStatus
from app.models.comment import Comment, CommentRead
from app.models.collect_task import CollectTask, CollectTaskCreate, CollectTaskRead, TaskStatus
from app.models.post_analysis import PostAnalysis, PostAnalysisRead
from app.models.opportunity import Opportunity, OpportunityRead, OpportunityListItem

__all__ = [
    "Subreddit", "SubredditCreate", "SubredditRead",
    "Post", "PostRead", "PostListItem", "AnalysisStatus",
    "Comment", "CommentRead",
    "CollectTask", "CollectTaskCreate", "CollectTaskRead", "TaskStatus",
    "PostAnalysis", "PostAnalysisRead",
    "Opportunity", "OpportunityRead", "OpportunityListItem",
]
