"""
Subreddit 管理 API：增删查改监控的版块列表及其采集配置。
"""
from typing import List
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.database import get_session
from app.models.subreddit import Subreddit, SubredditCreate, SubredditRead, SubredditUpdate

router = APIRouter(prefix="/api/subreddits", tags=["subreddits"])


@router.get("", response_model=List[SubredditRead])
def list_subreddits(session: Session = Depends(get_session)):
    """获取所有监控的 Subreddit 列表（含采集配置）。"""
    return session.exec(select(Subreddit).order_by(Subreddit.name)).all()


@router.post("", response_model=SubredditRead, status_code=201)
def create_subreddit(data: SubredditCreate, session: Session = Depends(get_session)):
    """
    添加一个新的 Subreddit 监控，并指定其默认采集参数。

    采集参数（均有默认值，可不传）：
    - sort_by: hot/new/top/rising（默认 hot）
    - time_filter: hour/day/week/month/year/all（仅 sort=top 时有效）
    - post_limit: 每次采集帖子数上限，1-100（默认 25）
    - fetch_comments: 是否采集评论（默认 True）
    - comment_min_score: 触发评论采集的帖子最低分（默认 5）
    - comment_min_count: 触发评论采集的最低评论数（默认 10）
    - comment_max_per_post: 每帖最多采集评论数（默认 200）
    """
    existing = session.exec(select(Subreddit).where(Subreddit.name == data.name)).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Subreddit '{data.name}' 已存在")
    sub = Subreddit(**data.model_dump())
    session.add(sub)
    session.commit()
    session.refresh(sub)
    return sub


@router.patch("/{subreddit_id}", response_model=SubredditRead)
def update_subreddit(
    subreddit_id: int,
    data: SubredditUpdate,
    session: Session = Depends(get_session),
):
    """
    更新 Subreddit 的采集配置（只传需要修改的字段，其余保持不变）。

    可更新字段：display_name / description / subscribers / is_active /
    sort_by / time_filter / post_limit / fetch_comments /
    comment_min_score / comment_min_count / comment_max_per_post
    """
    sub = session.get(Subreddit, subreddit_id)
    if not sub:
        raise HTTPException(status_code=404, detail="Subreddit 不存在")

    # 只更新显式传入的字段（exclude_unset 排除未传字段）
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(sub, field, value)

    sub.updated_at = datetime.now(timezone.utc)
    session.add(sub)
    session.commit()
    session.refresh(sub)
    return sub


@router.delete("/{subreddit_id}", status_code=204)
def delete_subreddit(subreddit_id: int, session: Session = Depends(get_session)):
    """删除一个 Subreddit 监控（不删除已采集的帖子）。"""
    sub = session.get(Subreddit, subreddit_id)
    if not sub:
        raise HTTPException(status_code=404, detail="Subreddit 不存在")
    session.delete(sub)
    session.commit()


@router.patch("/{subreddit_id}/toggle", response_model=SubredditRead)
def toggle_subreddit(subreddit_id: int, session: Session = Depends(get_session)):
    """切换 Subreddit 的启用/禁用状态。"""
    sub = session.get(Subreddit, subreddit_id)
    if not sub:
        raise HTTPException(status_code=404, detail="Subreddit 不存在")
    sub.is_active = not sub.is_active
    sub.updated_at = datetime.now(timezone.utc)
    session.add(sub)
    session.commit()
    session.refresh(sub)
    return sub
