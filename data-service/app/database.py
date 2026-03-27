"""
数据库连接和会话管理。
"""
from sqlmodel import SQLModel, create_engine, Session
from app.config import settings

# connect_args 仅 SQLite 需要，避免多线程检查
connect_args = {"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}

engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    connect_args=connect_args,
)


def create_db_and_tables() -> None:
    """创建所有数据表（若不存在）。"""
    SQLModel.metadata.create_all(engine)


def get_session():
    """FastAPI 依赖注入用的数据库会话生成器。"""
    with Session(engine) as session:
        yield session
