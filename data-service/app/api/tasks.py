"""
采集任务管理 API：创建、查询、触发、删除采集任务。

subreddit_name 为 null 的任务称为"全局任务"，执行时自动扫描所有 is_active=True 的 Subreddit，
每个频道使用其自身的采集配置（可被任务级参数覆盖）。
"""
import threading
import logging
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.database import get_session
from app.models.collect_task import CollectTask, CollectTaskCreate, CollectTaskRead, TaskStatus

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/tasks", tags=["tasks"])


def _execute_task(task_id: int) -> None:
    """
    后台执行采集任务（在独立线程中运行）。

    - 单频道任务（subreddit_name 非空）：使用任务自身的采集配置直接运行。
    - 全局任务（subreddit_name 为 null）：遍历所有 is_active 的 Subreddit，
      每个频道用"任务级参数覆盖频道默认值"的方式运行。
    """
    from app.database import engine
    from app.models.collect_task import CollectTask, TaskStatus
    from app.models.subreddit import Subreddit
    from app.services.collector import run_collection
    from sqlmodel import Session

    with Session(engine) as session:
        task = session.get(CollectTask, task_id)
        if not task:
            return

        task.status = TaskStatus.RUNNING
        task.updated_at = datetime.now(timezone.utc)
        session.add(task)
        session.commit()

        try:
            if task.subreddit_name is None:
                # ── 全局任务：遍历所有活跃频道 ──────────────────────────────
                active_subs = session.exec(
                    select(Subreddit).where(Subreddit.is_active == True)
                ).all()

                if not active_subs:
                    logger.warning("[task] 全局任务：没有启用的 Subreddit，跳过")
                    task.status = TaskStatus.COMPLETED
                    task.last_error = None
                else:
                    logger.info(f"[task] 全局任务：扫描 {len(active_subs)} 个频道")
                    total_inserted, total_comments = 0, 0
                    errors = []

                    for sub in active_subs:
                        # 任务级参数优先，未设置则使用频道默认值
                        effective_limit = task.post_limit or sub.post_limit
                        effective_sort = task.sort_by or sub.sort_by
                        effective_time_filter = task.time_filter or sub.time_filter
                        effective_fetch_comments = task.fetch_comments and sub.fetch_comments
                        effective_min_score = task.comment_min_score if task.comment_min_score is not None else sub.comment_min_score
                        effective_min_count = task.comment_min_count if task.comment_min_count is not None else sub.comment_min_count
                        effective_max_cmts = task.max_comments_per_post if task.max_comments_per_post is not None else sub.comment_max_per_post

                        try:
                            result = run_collection(
                                session=session,
                                subreddits=[sub.name],
                                limit=effective_limit,
                                sort=effective_sort,
                                fetch_comments=effective_fetch_comments,
                                time_filter=effective_time_filter,
                                comment_min_score=effective_min_score,
                                comment_min_count=effective_min_count,
                                max_comments_per_post=effective_max_cmts,
                            )
                            total_inserted += result["posts_inserted"]
                            total_comments += result["comments_collected"]
                            logger.info(
                                f"[task] 频道 {sub.name} 完成: "
                                f"posts={result['posts_inserted']}, comments={result['comments_collected']}"
                            )
                        except Exception as e:
                            logger.error(f"[task] 频道 {sub.name} 采集失败: {e}")
                            errors.append(f"{sub.name}: {e}")

                    task.status = TaskStatus.COMPLETED if not errors else TaskStatus.FAILED
                    task.last_error = "; ".join(errors)[:500] if errors else None
                    task.posts_collected += total_inserted
                    task.comments_collected += total_comments

            else:
                # ── 单频道任务：评论阈值优先级：任务级 > 频道默认 ────────────
                from sqlalchemy import func as sa_func
                sub = session.exec(
                    select(Subreddit).where(
                        sa_func.lower(Subreddit.name) == (task.subreddit_name or "").lower()
                    )
                ).first()

                # 若任务未显式设置，则从频道配置继承（全局 settings 作为最终兜底）
                effective_min_score = task.comment_min_score
                effective_min_count = task.comment_min_count
                effective_max_cmts  = task.max_comments_per_post

                if sub:
                    if effective_min_score is None:
                        effective_min_score = sub.comment_min_score
                    if effective_min_count is None:
                        effective_min_count = sub.comment_min_count
                    if effective_max_cmts is None:
                        effective_max_cmts = sub.comment_max_per_post

                result = run_collection(
                    session=session,
                    subreddits=[task.subreddit_name],
                    limit=task.post_limit,
                    sort=task.sort_by,
                    fetch_comments=task.fetch_comments,
                    time_filter=task.time_filter,
                    comment_min_score=effective_min_score,
                    comment_min_count=effective_min_count,
                    max_comments_per_post=effective_max_cmts,
                )
                task.status = TaskStatus.COMPLETED
                task.last_error = None
                task.posts_collected += result["posts_inserted"]
                task.comments_collected += result["comments_collected"]

        except Exception as e:
            logger.error(f"[task] 任务 {task_id} 执行失败: {e}")
            task.status = TaskStatus.FAILED
            task.last_error = str(e)[:500]
        finally:
            task.last_run_at = datetime.now(timezone.utc)
            task.updated_at = datetime.now(timezone.utc)
            session.add(task)
            session.commit()


@router.get("", response_model=List[CollectTaskRead])
def list_tasks(session: Session = Depends(get_session)):
    """获取所有采集任务列表。"""
    return session.exec(select(CollectTask).order_by(CollectTask.created_at.desc())).all()


@router.post("", response_model=CollectTaskRead, status_code=201)
def create_task(data: CollectTaskCreate, session: Session = Depends(get_session)):
    """
    创建新的采集任务。

    - subreddit_name 为 null → 全局任务（采集所有启用的频道）
    - subreddit_name 指定版块名 → 单频道任务
    - cron_expression 非空 → 定时自动触发；为空 → 仅手动触发
    - time_filter: hour/day/week/month/year/all（仅 sort=top 时有效）
    - comment_min_score / comment_min_count / max_comments_per_post：为 null 则继承频道配置
    """
    task = CollectTask(**data.model_dump())
    session.add(task)
    session.commit()
    session.refresh(task)
    return task


@router.get("/{task_id}", response_model=CollectTaskRead)
def get_task(task_id: int, session: Session = Depends(get_session)):
    """获取单个任务详情。"""
    task = session.get(CollectTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task


@router.post("/{task_id}/run", status_code=202)
def run_task(task_id: int, session: Session = Depends(get_session)):
    """手动触发执行采集任务（后台异步执行）。"""
    task = session.get(CollectTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if task.status == TaskStatus.RUNNING:
        raise HTTPException(status_code=409, detail="任务正在运行中，请稍后再试")

    thread = threading.Thread(target=_execute_task, args=(task_id,), daemon=True)
    thread.start()

    task_type = "全局" if task.subreddit_name is None else f"频道 {task.subreddit_name}"
    return {"message": f"采集任务已触发（{task_type}）", "task_id": task_id}


@router.patch("/{task_id}/toggle", response_model=CollectTaskRead)
def toggle_task(task_id: int, session: Session = Depends(get_session)):
    """启用/禁用任务的定时调度。"""
    task = session.get(CollectTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    task.is_active = not task.is_active
    task.updated_at = datetime.now(timezone.utc)
    session.add(task)
    session.commit()
    session.refresh(task)
    return task


@router.delete("/{task_id}", status_code=204)
def delete_task(task_id: int, session: Session = Depends(get_session)):
    """删除采集任务。"""
    task = session.get(CollectTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if task.status == TaskStatus.RUNNING:
        raise HTTPException(status_code=409, detail="任务正在运行中，无法删除")
    session.delete(task)
    session.commit()
