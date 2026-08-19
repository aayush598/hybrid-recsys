from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    All secrets and configuration are managed through environment variables.
    No hardcoded secrets anywhere in the codebase.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    APP_NAME: str = "BeautyRec"
    APP_VERSION: str = "1.0.0"
    APP_ENV: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent.parent

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 4
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # Database
    DATABASE_URL: str = f"sqlite+aiosqlite:///{Path(__file__).resolve().parent.parent.parent / 'data' / 'beautyrec.db'}"

    def model_post_init(self, __context: object) -> None:
        """Ensure the database directory exists."""
        db_url = self.DATABASE_URL
        if "sqlite" in db_url and ":///" in db_url:
            abs_path = Path(db_url.split(":///", 1)[1])
            abs_path.parent.mkdir(parents=True, exist_ok=True)
    DATABASE_ECHO: bool = False

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_CACHE_TTL: int = 3600

    # Security
    SECRET_KEY: str = "change-me-in-production-use-openssl-rand-hex-32"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    ALGORITHM: str = "HS256"

    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60

    # ML / Model
    MODEL_DIR: Path = Path("data/models")
    FAISS_INDEX_PATH: Path = Path("data/models/faiss_index")
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    CANDIDATE_POOL_SIZE: int = 500
    RANKING_TOP_K: int = 50
    DEFAULT_RECOMMENDATION_COUNT: int = 10

    # Dataset
    DATA_DIR: Path = Path("data")
    RAW_DATA_DIR: Path = Path("data/raw")
    PROCESSED_DATA_DIR: Path = Path("data/processed")
    MOVIELENS_URL: str = (
        "https://files.grouplens.org/datasets/movielens/ml-25m.zip"
    )

    # Feature Store
    FEATURE_STORE_ONLINE_TTL: int = 86400

    # Monitoring
    PROMETHEUS_ENABLED: bool = True
    ENABLE_REQUEST_LOGGING: bool = True

    # MLflow
    MLFLOW_TRACKING_URI: str = "http://localhost:5000"
    MLFLOW_EXPERIMENT_NAME: str = "beautyrec-production"

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def database_url_sync(self) -> str:
        return self.DATABASE_URL.replace("+aiosqlite", "")


@lru_cache
def get_settings() -> Settings:
    return Settings()
