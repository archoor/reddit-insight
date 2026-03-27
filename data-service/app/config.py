"""
应用配置管理，从环境变量加载所有配置项。
合并了原 data-service 和 insight-service 的全部配置。
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # ── 服务配置 ──────────────────────────────────────────────────────────────
    HOST: str = os.getenv("DATA_SERVICE_HOST", "0.0.0.0")
    PORT: int = int(os.getenv("DATA_SERVICE_PORT", "8001"))
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # ── 数据库 ────────────────────────────────────────────────────────────────
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./reddit_insight.db")

    # ── Apify 采集 ────────────────────────────────────────────────────────────
    APIFY_API_TOKEN: str = os.getenv("APIFY_API_TOKEN", "")
    APIFY_ACTOR_ID: str = os.getenv("APIFY_ACTOR_ID", "macrocosmos/reddit-scraper")

    # 采集参数
    DEFAULT_POST_LIMIT: int = int(os.getenv("DEFAULT_POST_LIMIT", "25"))
    DEFAULT_SORT: str = os.getenv("DEFAULT_SORT", "hot")
    COMMENT_FETCH_MIN_SCORE: int = int(os.getenv("COMMENT_FETCH_MIN_SCORE", "5"))
    COMMENT_FETCH_MIN_COMMENTS: int = int(os.getenv("COMMENT_FETCH_MIN_COMMENTS", "10"))
    MAX_COMMENTS_PER_POST: int = int(os.getenv("MAX_COMMENTS_PER_POST", "200"))

    # ── LLM 配置（LiteLLM 多模型支持）────────────────────────────────────────
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
    LLM_API_BASE: str = os.getenv("LLM_API_BASE", "")
    LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "4096"))
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.2"))

    # Token 预算（单次分析最大 input token）
    MAX_INPUT_TOKENS: int = int(os.getenv("MAX_INPUT_TOKENS", "80000"))
    # 每批最多送入的评论数
    MAX_COMMENTS_PER_BATCH: int = int(os.getenv("MAX_COMMENTS_PER_BATCH", "40"))
    # 采样后目标评论数
    SAMPLE_TARGET_COUNT: int = int(os.getenv("SAMPLE_TARGET_COUNT", "100"))

    # 商机评分阈值（高于此分才生成 Opportunity 记录）
    OPPORTUNITY_SCORE_THRESHOLD: int = int(os.getenv("OPPORTUNITY_SCORE_THRESHOLD", "50"))
    # 每帖最多生成商机数
    MAX_OPPORTUNITIES_PER_POST: int = int(os.getenv("MAX_OPPORTUNITIES_PER_POST", "5"))

    # 批量分析并发线程数
    ANALYSIS_MAX_WORKERS: int = int(os.getenv("ANALYSIS_MAX_WORKERS", "3"))

    # ── CORS ─────────────────────────────────────────────────────────────────
    CORS_ORIGINS: list = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")

    def __init__(self) -> None:
        # Gemini 专属：LiteLLM 要求使用 GEMINI_API_KEY 环境变量
        if self.LLM_MODEL.startswith("gemini/") and self.LLM_API_KEY:
            os.environ.setdefault("GEMINI_API_KEY", self.LLM_API_KEY)


settings = Settings()
