"""
Reddit Insight 统一后端入口：整合数据采集 + LLM 分析两大功能。

原 data-service (Port 8001) 和 insight-service (Port 8002) 已合并，
所有功能统一在 Port 8001 提供服务。
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import create_db_and_tables
from app.services.scheduler import init_scheduler, shutdown_scheduler
from app.api import subreddits, posts, tasks, stats, analysis, opportunities, reports

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理：启动时初始化 DB 和调度器，关闭时清理。"""
    logger.info("[main] Reddit Insight 后端服务启动中...")
    # 导入所有模型（确保 SQLModel 元数据包含所有表）
    import app.models  # noqa: F401
    create_db_and_tables()
    init_scheduler()
    logger.info("[main] 服务启动完成，监听 Port %d", settings.PORT)
    yield
    logger.info("[main] 服务关闭中...")
    shutdown_scheduler()


app = FastAPI(
    title="Reddit Insight",
    description="Reddit 商业洞见分析平台 — 数据采集 + LLM 分析一体化后端",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 数据采集路由 ──────────────────────────────────────────────────────────────
app.include_router(subreddits.router)
app.include_router(posts.router)
app.include_router(tasks.router)
app.include_router(stats.router)

# ── LLM 分析路由 ──────────────────────────────────────────────────────────────
app.include_router(analysis.router)
app.include_router(opportunities.router)
app.include_router(reports.router)


@app.get("/health")
def health_check():
    """健康检查端点。"""
    return {
        "status": "ok",
        "service": "reddit-insight-backend",
        "version": "2.0.0",
        "llm_model": settings.LLM_MODEL,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
