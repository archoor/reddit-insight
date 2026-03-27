"""
测试环境：独立 SQLite 文件、关闭调度器、每用例重置表结构。
必须在任何 app 导入之前设置 DATABASE_URL。
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

_fd, _TEST_DB_PATH_STR = tempfile.mkstemp(suffix=".db")
os.close(_fd)
TEST_DB_PATH = Path(_TEST_DB_PATH_STR)
os.environ["DATABASE_URL"] = "sqlite:///" + str(TEST_DB_PATH.resolve()).replace("\\", "/")


def pytest_sessionfinish(session, exitstatus):
    try:
        TEST_DB_PATH.unlink(missing_ok=True)
    except OSError:
        pass


@pytest.fixture(autouse=True)
def _disable_scheduler(monkeypatch: pytest.MonkeyPatch) -> None:
    """避免测试启动 BackgroundScheduler 与后台任务。"""
    monkeypatch.setattr("app.main.init_scheduler", lambda: None)
    monkeypatch.setattr("app.main.shutdown_scheduler", lambda: None)


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from app.main import app
    from app.database import engine
    from sqlmodel import SQLModel

    # 确保所有表模型已注册到 metadata
    from app.models.collect_task import CollectTask  # noqa: F401
    from app.models.comment import Comment  # noqa: F401
    from app.models.post import Post  # noqa: F401
    from app.models.subreddit import Subreddit  # noqa: F401

    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    with TestClient(app) as c:
        yield c
