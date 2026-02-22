from pathlib import Path
from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # App
    app_name: str = "AI Data Factory"
    app_version: str = "0.1.0"
    debug: bool = False

    # Database
    database_url: str = "sqlite+aiosqlite:///db/factory.db"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Logging
    log_level: str = "INFO"

    # Data paths
    data_dir: Path = Path("data")

    # Scraping defaults
    scraping_max_concurrent: int = 3
    scraping_rate_limit: float = 2.0
    scraping_retry_attempts: int = 3
    scraping_respect_robots_txt: bool = True
    scraping_use_playwright: str = "auto"

    # Processing defaults
    processing_chunk_size: int = 512
    processing_chunk_strategy: str = "recursive"
    processing_chunk_overlap: int = 50

    # Generation defaults
    generation_model: str = "gpt-4o-mini"
    generation_max_concurrent: int = 5
    generation_examples_per_chunk: int = 3
    openai_api_key: str = ""

    # Quality defaults
    quality_min_score: float = 0.7
    quality_checks: list[str] = ["toxicity", "readability", "format"]

    # Export defaults
    export_format: str = "jsonl"

    # HuggingFace
    huggingface_token: str = ""

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


@lru_cache
def get_settings() -> Settings:
    return Settings()
