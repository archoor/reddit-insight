"""
APScheduler 定时调度服务。
启动时读取所有 is_active=True 且有 cron_expression 的任务，注册定时调度。
"""
import logging
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlmodel import Session, select

from app.database import engine
from app.models.collect_task import CollectTask, TaskStatus

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler(timezone="UTC")


def _run_task_by_id(task_id: int) -> None:
    """定时调度触发的任务执行函数。"""
    from app.api.tasks import _execute_task
    logger.info(f"[scheduler] 定时触发任务 id={task_id}")
    _execute_task(task_id)


def register_task(task: CollectTask) -> None:
    """向调度器注册单个任务的定时规则。"""
    if not task.cron_expression or not task.is_active:
        return
    job_id = f"task_{task.id}"
    try:
        trigger = CronTrigger.from_crontab(task.cron_expression, timezone="UTC")
        scheduler.add_job(
            _run_task_by_id,
            trigger=trigger,
            args=[task.id],
            id=job_id,
            replace_existing=True,
            name=f"collect:{task.subreddit_name}",
        )
        logger.info(f"[scheduler] 已注册任务 job_id={job_id}, cron={task.cron_expression}")
    except Exception as e:
        logger.error(f"[scheduler] 任务 {task.id} 注册失败: {e}")


def unregister_task(task_id: int) -> None:
    """从调度器移除任务。"""
    job_id = f"task_{task_id}"
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
        logger.info(f"[scheduler] 已移除任务 job_id={job_id}")


def init_scheduler() -> None:
    """
    应用启动时调用：加载数据库中所有有效的定时任务并注册到调度器。
    """
    with Session(engine) as session:
        tasks = session.exec(
            select(CollectTask).where(
                CollectTask.is_active == True,
                CollectTask.cron_expression.is_not(None),
            )
        ).all()
        for task in tasks:
            register_task(task)

    scheduler.start()
    logger.info(f"[scheduler] 调度器已启动，共注册 {len(tasks)} 个定时任务")


def shutdown_scheduler() -> None:
    """应用关闭时调用：停止调度器。"""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("[scheduler] 调度器已停止")
