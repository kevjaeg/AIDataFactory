# AI Data Factory — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a production-grade data pipeline that scrapes web content, cleans it, generates LLM training data, runs quality control, and exports results — all orchestrated via a JARVIS-style dashboard.

**Architecture:** Worker-separation pattern with 4 Docker containers (FastAPI API, Pipeline Worker, Redis, Next.js Frontend). Pipeline has 5 stages (Spider→Refiner→Factory→Inspector→Shipper) coordinated by an Orchestrator. SQLite for persistence, Redis for job queue + pub/sub.

**Tech Stack:** Python 3.12+ / FastAPI / SQLAlchemy (async) / Redis / Playwright / httpx / trafilatura / tiktoken / litellm / detoxify / textstat / Next.js 15 / Tailwind v4 / ShadCN / Recharts / Docker Compose

**Reference:** `docs/plans/2026-02-21-ai-data-factory-design.md`

---

## Stage 1: Foundation (Backend + DB + Config + Redis + Logging)

### Task 1: Initialize Python project

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/src/__init__.py`
- Create: `backend/src/main.py`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/conftest.py`
- Create: `.gitignore`

**Step 1: Create `.gitignore`**

```gitignore
# Python
__pycache__/
*.py[cod]
*.egg-info/
dist/
.venv/
venv/

# Environment
.env
.env.local

# Data
backend/data/raw/
backend/data/processed/
backend/data/generated/
backend/data/exports/
backend/data/logs/
db/*.db
db/*.db-wal
db/*.db-shm

# IDE
.vscode/
.idea/

# OS
.DS_Store
Thumbs.db

# Node
node_modules/
.next/

# Docker
docker-compose.override.yml

# Firebase
firebase-debug.log
```

**Step 2: Create `backend/pyproject.toml`**

```toml
[project]
name = "ai-data-factory"
version = "0.1.0"
description = "Production-grade AI training data pipeline"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.34.0",
    "sqlalchemy[asyncio]>=2.0.36",
    "aiosqlite>=0.21.0",
    "pydantic>=2.10.0",
    "pydantic-settings>=2.7.0",
    "redis>=5.2.0",
    "httpx>=0.28.0",
    "loguru>=0.7.3",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.25.0",
    "pytest-httpx>=0.35.0",
    "httpx>=0.28.0",
    "ruff>=0.8.0",
]
pipeline = [
    "playwright>=1.49.0",
    "trafilatura>=2.0.0",
    "beautifulsoup4>=4.12.0",
    "tiktoken>=0.8.0",
    "langchain-text-splitters>=0.3.0",
    "litellm>=1.55.0",
    "jinja2>=3.1.0",
    "detoxify>=0.5.0",
    "textstat>=0.7.0",
    "datasketch>=1.6.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
pythonpath = ["src"]

[tool.ruff]
target-version = "py312"
line-length = 100
```

**Step 3: Create minimal `backend/src/__init__.py`**

```python
```

**Step 4: Create minimal `backend/src/main.py`**

```python
from fastapi import FastAPI

app = FastAPI(
    title="AI Data Factory",
    version="0.1.0",
    description="Production-grade AI training data pipeline",
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
```

**Step 5: Create `backend/tests/__init__.py` and `backend/tests/conftest.py`**

```python
# tests/__init__.py
```

```python
# tests/conftest.py
import pytest
from httpx import ASGITransport, AsyncClient

from main import app


@pytest.fixture
async def client() -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
```

**Step 6: Create venv, install deps, run health test**

```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate  # Windows Git Bash
pip install -e ".[dev]"
```

**Step 7: Write and run first test**

Create `backend/tests/test_health.py`:

```python
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_returns_ok(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

Run: `cd backend && python -m pytest tests/test_health.py -v`
Expected: PASS

**Step 8: Commit**

```bash
git add -A
git commit -m "feat: initialize backend project with FastAPI and health endpoint"
```

---

### Task 2: Config & Settings

**Files:**
- Create: `backend/src/config.py`
- Create: `backend/.env.example`
- Test: `backend/tests/test_config.py`

**Step 1: Write the failing test**

```python
# tests/test_config.py
from config import Settings


def test_settings_defaults() -> None:
    settings = Settings(
        _env_file=None,  # Don't read .env in tests
    )
    assert settings.app_name == "AI Data Factory"
    assert settings.database_url.endswith("factory.db")
    assert settings.redis_url == "redis://localhost:6379/0"
    assert settings.log_level == "INFO"


def test_settings_scraping_defaults() -> None:
    settings = Settings(_env_file=None)
    assert settings.scraping_max_concurrent == 3
    assert settings.scraping_rate_limit == 2.0
    assert settings.scraping_respect_robots_txt is True


def test_settings_generation_defaults() -> None:
    settings = Settings(_env_file=None)
    assert settings.generation_model == "gpt-4o-mini"
    assert settings.generation_max_concurrent == 5
    assert settings.quality_min_score == 0.7
```

**Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_config.py -v`
Expected: FAIL (config module not found)

**Step 3: Implement config**

```python
# src/config.py
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
    scraping_rate_limit: float = 2.0  # requests per second per domain
    scraping_retry_attempts: int = 3
    scraping_respect_robots_txt: bool = True
    scraping_use_playwright: str = "auto"  # "auto", "always", "never"

    # Processing defaults
    processing_chunk_size: int = 512  # tokens
    processing_chunk_strategy: str = "recursive"
    processing_chunk_overlap: int = 50  # tokens

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

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

**Step 4: Create `.env.example`**

```env
# AI Data Factory Configuration

# Debug mode (set to true for development)
DEBUG=false

# Database (SQLite path)
DATABASE_URL=sqlite+aiosqlite:///db/factory.db

# Redis
REDIS_URL=redis://localhost:6379/0

# Logging
LOG_LEVEL=INFO

# OpenAI API Key (required for training data generation)
OPENAI_API_KEY=sk-your-key-here

# Generation
GENERATION_MODEL=gpt-4o-mini
GENERATION_MAX_CONCURRENT=5
GENERATION_EXAMPLES_PER_CHUNK=3

# Quality Control
QUALITY_MIN_SCORE=0.7

# Scraping
SCRAPING_MAX_CONCURRENT=3
SCRAPING_RATE_LIMIT=2.0
```

**Step 5: Run tests**

Run: `cd backend && python -m pytest tests/test_config.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add backend/src/config.py backend/.env.example backend/tests/test_config.py
git commit -m "feat: add application settings with pydantic-settings"
```

---

### Task 3: Logging with loguru

**Files:**
- Create: `backend/src/logging_config.py`
- Modify: `backend/src/main.py`
- Test: `backend/tests/test_logging.py`

**Step 1: Write the failing test**

```python
# tests/test_logging.py
from loguru import logger

from logging_config import setup_logging


def test_setup_logging_configures_loguru() -> None:
    setup_logging(level="DEBUG")
    # Verify logger is usable after setup
    with logger.catch():
        logger.info("Test message")
    # If we got here without error, logging is configured
    assert True


def test_setup_logging_accepts_level() -> None:
    setup_logging(level="WARNING")
    # Should not raise
    assert True
```

**Step 2: Implement logging setup**

```python
# src/logging_config.py
import sys

from loguru import logger


def setup_logging(level: str = "INFO") -> None:
    """Configure loguru for the application."""
    logger.remove()  # Remove default handler
    logger.add(
        sys.stderr,
        level=level,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        ),
        colorize=True,
    )
    logger.add(
        "data/logs/factory_{time:YYYY-MM-DD}.log",
        level=level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        rotation="1 day",
        retention="7 days",
        compression="zip",
    )
```

**Step 3: Wire logging into FastAPI app**

Update `backend/src/main.py` — add `setup_logging()` call in lifespan.

**Step 4: Run tests, commit**

Run: `cd backend && python -m pytest tests/ -v`

```bash
git add backend/src/logging_config.py backend/src/main.py backend/tests/test_logging.py
git commit -m "feat: add structured logging with loguru"
```

---

### Task 4: Database models with SQLAlchemy

**Files:**
- Create: `backend/src/db/__init__.py`
- Create: `backend/src/db/database.py`
- Create: `backend/src/db/models.py`
- Test: `backend/tests/test_db.py`

**Step 1: Write the failing test**

```python
# tests/test_db.py
import pytest
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from db.models import Base, Project, Job, RawDocument, Chunk, TrainingExample, Export


@pytest.fixture
async def engine():
    eng = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest.fixture
async def session(engine):
    async with AsyncSession(engine) as s:
        yield s


async def test_all_tables_created(engine) -> None:
    async with engine.connect() as conn:
        tables = await conn.run_sync(
            lambda sync_conn: inspect(sync_conn).get_table_names()
        )
    expected = {"projects", "jobs", "raw_documents", "chunks", "training_examples", "exports"}
    assert expected == set(tables)


async def test_create_project(session: AsyncSession) -> None:
    project = Project(name="Test Project", description="A test")
    session.add(project)
    await session.commit()
    await session.refresh(project)
    assert project.id is not None
    assert project.name == "Test Project"
    assert project.created_at is not None


async def test_create_job_for_project(session: AsyncSession) -> None:
    project = Project(name="Test")
    session.add(project)
    await session.commit()
    await session.refresh(project)

    job = Job(project_id=project.id, status="pending", config={"urls": ["https://example.com"]})
    session.add(job)
    await session.commit()
    await session.refresh(job)
    assert job.id is not None
    assert job.status == "pending"
    assert job.project_id == project.id
```

**Step 2: Implement database module**

```python
# src/db/__init__.py
```

```python
# src/db/database.py
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config import get_settings

_engine = None
_session_factory = None


async def init_db() -> None:
    """Initialize database engine and create tables."""
    global _engine, _session_factory
    from db.models import Base

    settings = get_settings()
    _engine = create_async_engine(
        settings.database_url,
        echo=settings.debug,
        connect_args={"check_same_thread": False},
    )
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)

    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Enable WAL mode for concurrent reads
    async with _engine.begin() as conn:
        await conn.execute(
            __import__("sqlalchemy").text("PRAGMA journal_mode=WAL")
        )


async def close_db() -> None:
    """Close database engine."""
    global _engine
    if _engine:
        await _engine.dispose()


async def get_session() -> AsyncSession:
    """Get a database session."""
    if _session_factory is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    async with _session_factory() as session:
        yield session
```

```python
# src/db/models.py
from datetime import datetime, timezone

from sqlalchemy import JSON, Float, Integer, String, Text, Boolean
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    stage: Mapped[str | None] = mapped_column(String(50), nullable=True)
    config: Mapped[dict] = mapped_column(JSON, nullable=False)
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    cost_total: Mapped[float] = mapped_column(Float, default=0.0)
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc)
    )


class RawDocument(Base):
    __tablename__ = "raw_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(Integer, nullable=False)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    html_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    language: Mapped[str | None] = mapped_column(String(10), nullable=True)
    scrape_status: Mapped[str] = mapped_column(String(50), default="pending")
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc)
    )


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc)
    )


class TrainingExample(Base):
    __tablename__ = "training_examples"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chunk_id: Mapped[int] = mapped_column(Integer, nullable=False)
    job_id: Mapped[int] = mapped_column(Integer, nullable=False)
    template_type: Mapped[str] = mapped_column(String(50), nullable=False)
    input_text: Mapped[str] = mapped_column(Text, nullable=False)
    output_text: Mapped[str] = mapped_column(Text, nullable=False)
    model_used: Mapped[str] = mapped_column(String(100), nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, default=0)
    cost: Mapped[float] = mapped_column(Float, default=0.0)
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    quality_details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    passed_qc: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc)
    )


class Export(Base):
    __tablename__ = "exports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(Integer, nullable=False)
    format: Mapped[str] = mapped_column(String(20), nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    record_count: Mapped[int] = mapped_column(Integer, default=0)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    dataset_card: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc)
    )
```

**Step 3: Run tests, commit**

Run: `cd backend && python -m pytest tests/test_db.py -v`

```bash
git add backend/src/db/ backend/tests/test_db.py
git commit -m "feat: add SQLAlchemy database models for all 6 tables"
```

---

### Task 5: Redis client

**Files:**
- Create: `backend/src/clients/__init__.py`
- Create: `backend/src/clients/redis_client.py`
- Test: `backend/tests/test_redis_client.py`

**Step 1: Write the failing test**

```python
# tests/test_redis_client.py
import pytest
from unittest.mock import AsyncMock, patch

from clients.redis_client import RedisClient


async def test_redis_client_publish() -> None:
    client = RedisClient.__new__(RedisClient)
    client._redis = AsyncMock()
    await client.publish("test-channel", {"status": "ok"})
    client._redis.publish.assert_called_once()


async def test_redis_client_enqueue_job() -> None:
    client = RedisClient.__new__(RedisClient)
    client._redis = AsyncMock()
    await client.enqueue_job(job_id=1, config={"urls": ["https://example.com"]})
    client._redis.lpush.assert_called_once()
```

**Step 2: Implement Redis client**

```python
# src/clients/__init__.py
```

```python
# src/clients/redis_client.py
import json

import redis.asyncio as redis
from loguru import logger

from config import get_settings


class RedisClient:
    """Async Redis client for job queue and pub/sub."""

    def __init__(self) -> None:
        settings = get_settings()
        self._redis = redis.from_url(settings.redis_url, decode_responses=True)

    async def ping(self) -> bool:
        """Check Redis connection."""
        try:
            return await self._redis.ping()
        except redis.ConnectionError:
            return False

    async def enqueue_job(self, job_id: int, config: dict) -> None:
        """Push a job onto the pipeline queue."""
        payload = json.dumps({"job_id": job_id, "config": config})
        await self._redis.lpush("pipeline:jobs", payload)
        logger.info(f"Enqueued job {job_id}")

    async def dequeue_job(self, timeout: int = 0) -> dict | None:
        """Pop a job from the pipeline queue. Blocks for `timeout` seconds."""
        result = await self._redis.brpop("pipeline:jobs", timeout=timeout)
        if result:
            _, payload = result
            return json.loads(payload)
        return None

    async def publish(self, channel: str, data: dict) -> None:
        """Publish progress update to a channel."""
        await self._redis.publish(channel, json.dumps(data))

    async def close(self) -> None:
        """Close Redis connection."""
        await self._redis.close()
```

**Step 3: Run tests, commit**

Run: `cd backend && python -m pytest tests/test_redis_client.py -v`

```bash
git add backend/src/clients/ backend/tests/test_redis_client.py
git commit -m "feat: add async Redis client for job queue and pub/sub"
```

---

### Task 6: Wire up FastAPI app with lifespan

**Files:**
- Modify: `backend/src/main.py` — add lifespan, CORS, router structure
- Create: `backend/src/api/__init__.py`
- Create: `backend/src/api/routes/__init__.py`
- Create: `backend/src/api/routes/health.py`
- Update: `backend/tests/conftest.py` — use lifespan-aware test setup
- Test: `backend/tests/test_health.py` — update for expanded health endpoint

**Step 1: Implement full `main.py` with lifespan**

```python
# src/main.py
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from config import get_settings
from logging_config import setup_logging
from db.database import init_db, close_db
from api.routes import health


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    settings = get_settings()
    setup_logging(level=settings.log_level)
    logger.info("Starting AI Data Factory API...")

    # Ensure data directories exist
    for subdir in ["raw", "processed", "generated", "exports", "logs"]:
        (settings.data_dir / subdir).mkdir(parents=True, exist_ok=True)
    Path("db").mkdir(parents=True, exist_ok=True)

    # Initialize database
    await init_db()
    logger.info("Database initialized")

    yield

    # Shutdown
    await close_db()
    logger.info("AI Data Factory API stopped")


app = FastAPI(
    title="AI Data Factory",
    version="0.1.0",
    description="Production-grade AI training data pipeline",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(health.router)
```

**Step 2: Create health router with Redis/DB check**

```python
# src/api/__init__.py
```

```python
# src/api/routes/__init__.py
```

```python
# src/api/routes/health.py
from fastapi import APIRouter

from db.database import _engine

router = APIRouter()


@router.get("/health")
async def health_check() -> dict:
    """Health check endpoint with component status."""
    checks: dict[str, str] = {}

    # Database check
    try:
        if _engine:
            async with _engine.connect() as conn:
                await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
            checks["database"] = "ok"
        else:
            checks["database"] = "not_initialized"
    except Exception:
        checks["database"] = "error"

    # Redis check (best-effort, not critical for health)
    try:
        from clients.redis_client import RedisClient
        rc = RedisClient()
        if await rc.ping():
            checks["redis"] = "ok"
        else:
            checks["redis"] = "unreachable"
        await rc.close()
    except Exception:
        checks["redis"] = "unavailable"

    overall = "ok" if checks.get("database") == "ok" else "degraded"

    return {"status": overall, "components": checks}
```

**Step 3: Update conftest for lifespan**

```python
# tests/conftest.py
import pytest
from httpx import ASGITransport, AsyncClient

from main import app


@pytest.fixture
async def client() -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
```

**Step 4: Update health test**

```python
# tests/test_health.py
import pytest
from httpx import AsyncClient


async def test_health_returns_status(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "components" in data
    assert data["components"]["database"] in ("ok", "not_initialized")
```

**Step 5: Run all tests, commit**

Run: `cd backend && python -m pytest tests/ -v`

```bash
git add backend/src/ backend/tests/
git commit -m "feat: wire up FastAPI lifespan with DB init, CORS, and health router"
```

---

### Task 7: Pydantic schemas for API

**Files:**
- Create: `backend/src/api/schemas.py`
- Test: `backend/tests/test_schemas.py`

**Step 1: Implement API schemas**

These Pydantic models define the API request/response contracts.

```python
# src/api/schemas.py
from datetime import datetime
from pydantic import BaseModel, Field


# --- Config Sub-Schemas ---

class ScrapingConfig(BaseModel):
    max_concurrent: int = 3
    use_playwright: str = "auto"
    respect_robots_txt: bool = True
    rate_limit: float = 2.0

class ProcessingConfig(BaseModel):
    chunk_size: int = 512
    chunk_strategy: str = "recursive"
    chunk_overlap: int = 50

class GenerationConfig(BaseModel):
    template: str = "qa"
    model: str = "gpt-4o-mini"
    examples_per_chunk: int = 3
    max_concurrent_llm: int = 5

class QualityConfig(BaseModel):
    min_score: float = 0.7
    checks: list[str] = ["toxicity", "readability", "format"]

class ExportConfig(BaseModel):
    format: str = "jsonl"

class PipelineConfig(BaseModel):
    scraping: ScrapingConfig = ScrapingConfig()
    processing: ProcessingConfig = ProcessingConfig()
    generation: GenerationConfig = GenerationConfig()
    quality: QualityConfig = QualityConfig()
    export: ExportConfig = ExportConfig()


# --- Project ---

class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    config: dict | None = None

class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    config: dict | None = None

class ProjectResponse(BaseModel):
    id: int
    name: str
    description: str | None
    config: dict | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# --- Job ---

class JobCreate(BaseModel):
    urls: list[str] = Field(..., min_length=1)
    config: PipelineConfig = PipelineConfig()

class JobResponse(BaseModel):
    id: int
    project_id: int
    status: str
    stage: str | None
    config: dict
    progress: float
    error: str | None
    cost_total: float
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Export ---

class ExportResponse(BaseModel):
    id: int
    job_id: int
    format: str
    file_path: str
    record_count: int
    version: str
    dataset_card: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Stats ---

class StatsOverview(BaseModel):
    total_projects: int
    total_jobs: int
    active_jobs: int
    total_examples: int
    total_cost: float
```

**Step 2: Write schema validation tests**

```python
# tests/test_schemas.py
from api.schemas import JobCreate, PipelineConfig, ProjectCreate


def test_job_create_minimal() -> None:
    job = JobCreate(urls=["https://example.com"])
    assert job.config.scraping.max_concurrent == 3
    assert job.config.generation.model == "gpt-4o-mini"
    assert job.config.quality.min_score == 0.7


def test_job_create_custom_config() -> None:
    job = JobCreate(
        urls=["https://example.com"],
        config=PipelineConfig(
            generation={"template": "summarization", "model": "gpt-4o"},
        ),
    )
    assert job.config.generation.template == "summarization"
    assert job.config.generation.model == "gpt-4o"
    # Defaults preserved for unset fields
    assert job.config.scraping.max_concurrent == 3


def test_project_create_validation() -> None:
    project = ProjectCreate(name="My Project", description="Test")
    assert project.name == "My Project"


def test_job_create_requires_urls() -> None:
    import pytest
    with pytest.raises(Exception):
        JobCreate(urls=[])
```

**Step 3: Run tests, commit**

Run: `cd backend && python -m pytest tests/test_schemas.py -v`

```bash
git add backend/src/api/schemas.py backend/tests/test_schemas.py
git commit -m "feat: add Pydantic API schemas with sensible defaults"
```

---

### Task 8: Project CRUD routes

**Files:**
- Create: `backend/src/api/routes/projects.py`
- Modify: `backend/src/main.py` — register projects router
- Test: `backend/tests/test_api/test_projects.py`

**Step 1: Write failing tests**

```python
# tests/test_api/__init__.py
```

```python
# tests/test_api/test_projects.py
import pytest
from httpx import AsyncClient


async def test_create_project(client: AsyncClient) -> None:
    response = await client.post("/api/projects", json={
        "name": "Test Project",
        "description": "A test project",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Project"
    assert data["id"] is not None


async def test_list_projects(client: AsyncClient) -> None:
    # Create two projects
    await client.post("/api/projects", json={"name": "Project 1"})
    await client.post("/api/projects", json={"name": "Project 2"})

    response = await client.get("/api/projects")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2


async def test_get_project(client: AsyncClient) -> None:
    create = await client.post("/api/projects", json={"name": "Get Me"})
    project_id = create.json()["id"]

    response = await client.get(f"/api/projects/{project_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "Get Me"


async def test_get_nonexistent_project(client: AsyncClient) -> None:
    response = await client.get("/api/projects/99999")
    assert response.status_code == 404


async def test_delete_project(client: AsyncClient) -> None:
    create = await client.post("/api/projects", json={"name": "Delete Me"})
    project_id = create.json()["id"]

    response = await client.delete(f"/api/projects/{project_id}")
    assert response.status_code == 204

    response = await client.get(f"/api/projects/{project_id}")
    assert response.status_code == 404
```

**Step 2: Implement projects router**

```python
# src/api/routes/projects.py
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas import ProjectCreate, ProjectUpdate, ProjectResponse
from db.database import get_session
from db.models import Project

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.post("", status_code=201, response_model=ProjectResponse)
async def create_project(
    body: ProjectCreate,
    session: AsyncSession = Depends(get_session),
) -> Project:
    project = Project(**body.model_dump())
    session.add(project)
    await session.commit()
    await session.refresh(project)
    return project


@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    session: AsyncSession = Depends(get_session),
) -> list[Project]:
    result = await session.execute(select(Project).order_by(Project.created_at.desc()))
    return list(result.scalars().all())


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: int,
    session: AsyncSession = Depends(get_session),
) -> Project:
    project = await session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: int,
    body: ProjectUpdate,
    session: AsyncSession = Depends(get_session),
) -> Project:
    project = await session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(project, key, value)
    await session.commit()
    await session.refresh(project)
    return project


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: int,
    session: AsyncSession = Depends(get_session),
) -> Response:
    project = await session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    await session.delete(project)
    await session.commit()
    return Response(status_code=204)
```

**Step 3: Register router in `main.py`**

Add to main.py: `from api.routes import health, projects` and `app.include_router(projects.router)`

**Step 4: Update conftest for DB isolation**

The conftest needs to set up an in-memory DB per test to avoid cross-test pollution. Override the `get_session` dependency to use an in-memory SQLite engine.

**Step 5: Run tests, commit**

Run: `cd backend && python -m pytest tests/test_api/ -v`

```bash
git add backend/src/api/routes/projects.py backend/tests/test_api/ backend/src/main.py
git commit -m "feat: add project CRUD API routes"
```

---

## Stage 2: Spider (Ingestion Engine)

### Task 9: Pipeline stage protocol + base class

**Files:**
- Create: `backend/src/pipeline/__init__.py`
- Create: `backend/src/pipeline/base.py`
- Test: `backend/tests/test_pipeline/__init__.py`
- Test: `backend/tests/test_pipeline/test_base.py`

Define the `PipelineStage` protocol and `StageResult` model that all 5 stages implement. This is the contract every stage follows:

```python
# src/pipeline/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class StageResult:
    """Result from a pipeline stage execution."""
    success: bool
    data: list[Any] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)


class PipelineStage(ABC):
    """Base class for all pipeline stages."""

    stage_name: str

    @abstractmethod
    async def process(self, input_data: Any, config: dict) -> StageResult:
        """Process input data and return results."""
        ...

    @abstractmethod
    async def validate_input(self, input_data: Any) -> bool:
        """Validate input before processing."""
        ...
```

Test that the protocol is usable by creating a minimal mock stage. Commit.

```bash
git commit -m "feat: add pipeline stage base class and protocol"
```

---

### Task 10: Scraper client (httpx + Playwright fallback)

**Files:**
- Create: `backend/src/clients/scraper_client.py`
- Test: `backend/tests/test_clients/test_scraper.py`

Implement `ScraperClient` with:
- `async def scrape_url(url, use_playwright="auto") -> ScrapeResult`
- httpx GET as first attempt (fast path)
- If response looks like JS-rendered (empty body, meta refresh), fall back to Playwright
- Retry logic: 3 attempts, exponential backoff (1s, 2s, 4s)
- robots.txt check via `urllib.robotparser`
- Returns `ScrapeResult(url, html, status_code, method_used, error)`

Test with `pytest-httpx` for mocking HTTP responses. Playwright tests should be marked with `@pytest.mark.slow` and only run when Playwright is installed.

```bash
git commit -m "feat: add scraper client with httpx and Playwright fallback"
```

---

### Task 11: Rate limiter

**Files:**
- Create: `backend/src/pipeline/rate_limiter.py`
- Test: `backend/tests/test_pipeline/test_rate_limiter.py`

Implement per-domain rate limiting using an asyncio semaphore + token bucket:
- `RateLimiter.acquire(domain)` — awaits until allowed
- Configurable rate per domain (default: 2 req/sec)
- Uses `asyncio.Semaphore` for concurrency + `asyncio.sleep` for rate

```bash
git commit -m "feat: add per-domain async rate limiter"
```

---

### Task 12: Spider stage (ingestion.py)

**Files:**
- Create: `backend/src/pipeline/stages/__init__.py`
- Create: `backend/src/pipeline/stages/ingestion.py`
- Test: `backend/tests/test_pipeline/test_ingestion.py`

The Spider stage orchestrates scraping a list of URLs:
1. Validate URLs
2. Check robots.txt per domain
3. Apply rate limiting
4. Scrape each URL (httpx → Playwright fallback)
5. Extract metadata (title, language from HTTP headers)
6. Save raw HTML to `data/raw/{job_id}/{hash}.html`
7. Return `StageResult` with `List[RawDocument]`

```bash
git commit -m "feat: add Spider ingestion stage"
```

---

### Task 13: Jobs API route (start pipeline)

**Files:**
- Create: `backend/src/api/routes/jobs.py`
- Modify: `backend/src/main.py` — register jobs router
- Test: `backend/tests/test_api/test_jobs.py`

POST `/api/projects/{id}/jobs` should:
1. Validate project exists
2. Create Job record in DB with status "pending"
3. Enqueue job to Redis
4. Return JobResponse

GET `/api/jobs/{id}` returns job status + progress.

```bash
git commit -m "feat: add jobs API routes with Redis enqueue"
```

---

## Stage 3: Refiner (Processing Pipeline)

### Task 14: Content extraction with trafilatura

**Files:**
- Create: `backend/src/pipeline/stages/processing.py`
- Test: `backend/tests/test_pipeline/test_processing.py`

The Refiner stage:
1. Read raw HTML from file
2. Extract main content via `trafilatura.extract()` with metadata
3. Fallback: BeautifulSoup4 if trafilatura returns nothing
4. Detect language via trafilatura's built-in detection
5. Chunk text using `langchain_text_splitters.RecursiveCharacterTextSplitter` with tiktoken token counting
6. Count tokens per chunk via `tiktoken.encoding_for_model("gpt-4o-mini")`
7. Deduplicate chunks (exact + near-duplicate via MinHash from `datasketch`)
8. Save chunks to DB
9. Return `StageResult` with `List[ProcessedDocument]`

Test with sample HTML fixtures (create `tests/fixtures/sample_article.html`).

```bash
git commit -m "feat: add Refiner processing stage with chunking and dedup"
```

---

## Stage 4: Factory (Training Data Generator)

### Task 15: LLM client with litellm

**Files:**
- Create: `backend/src/clients/llm_client.py`
- Test: `backend/tests/test_clients/test_llm_client.py`

Wrapper around litellm for:
- `async def complete(prompt, model, temperature) -> LLMResponse`
- Token counting per request/response
- Cost calculation using litellm's built-in cost tracking
- Retry logic for rate limits (429s)
- Configurable concurrency via semaphore

Test with mocked litellm responses.

```bash
git commit -m "feat: add LLM client wrapper with cost tracking"
```

---

### Task 16: Prompt template system

**Files:**
- Create: `backend/src/templates/__init__.py`
- Create: `backend/src/templates/base.py`
- Create: `backend/src/templates/qa_generation.py`
- Create: `backend/src/templates/summarization.py`
- Create: `backend/src/templates/classification.py`
- Create: `backend/src/templates/instruction_following.py`
- Test: `backend/tests/test_templates.py`

Jinja2-based template system:
- Each template defines: `system_prompt`, `user_prompt_template`, `output_schema`
- `TemplateRegistry` maps template names to classes
- Templates render with chunk content + metadata as context
- Output parsing: extract structured data from LLM response (JSON mode)

The 4 built-in templates:
- **Q&A:** Generates question-answer pairs from content
- **Summarization:** Generates (long_text, summary) pairs
- **Classification:** Generates (text, label) pairs with configurable labels
- **Instruction-Following:** Generates (instruction, response) pairs

```bash
git commit -m "feat: add Jinja2 prompt template system with 4 built-in templates"
```

---

### Task 17: Factory stage (generation.py)

**Files:**
- Create: `backend/src/pipeline/stages/generation.py`
- Test: `backend/tests/test_pipeline/test_generation.py`

The Factory stage:
1. Load configured template
2. For each chunk: render prompt → call LLM → parse response
3. Batch processing with configurable concurrency (asyncio.Semaphore)
4. Track tokens + cost per example
5. Save TrainingExample records to DB
6. Return `StageResult` with stats (total_examples, total_tokens, total_cost)

```bash
git commit -m "feat: add Factory generation stage with batch processing"
```

---

## Stage 5: Inspector (Quality Control)

### Task 18: Quality checkers

**Files:**
- Create: `backend/src/pipeline/stages/quality.py`
- Create: `backend/src/pipeline/quality_checks/__init__.py`
- Create: `backend/src/pipeline/quality_checks/toxicity.py`
- Create: `backend/src/pipeline/quality_checks/readability.py`
- Create: `backend/src/pipeline/quality_checks/format_check.py`
- Create: `backend/src/pipeline/quality_checks/duplicate_check.py`
- Test: `backend/tests/test_pipeline/test_quality.py`

Individual quality checkers:
- **ToxicityChecker:** Uses `detoxify` to score toxicity (0-1, lower is better)
- **ReadabilityChecker:** Uses `textstat` for Flesch reading ease (normalize to 0-1)
- **FormatChecker:** Validates that input/output match expected schema
- **DuplicateChecker:** Cosine similarity between examples (flag near-duplicates)

Inspector stage:
1. Run all configured checks on each TrainingExample
2. Compute aggregate quality_score (weighted average)
3. Mark `passed_qc` based on threshold
4. Store quality_details JSON
5. Return `StageResult` with pass/fail stats

```bash
git commit -m "feat: add Inspector quality control stage with 4 checkers"
```

---

## Stage 6: Shipper (Export Engine)

### Task 19: Export stage

**Files:**
- Create: `backend/src/pipeline/stages/export.py`
- Create: `backend/src/api/routes/exports.py`
- Test: `backend/tests/test_pipeline/test_export.py`

The Shipper stage:
1. Query all TrainingExamples for the job where `passed_qc = True`
2. Format into target format (JSON, JSONL, CSV)
3. Generate dataset card (Markdown with stats)
4. Save to `data/exports/{job_id}/{version}.{format}`
5. Create Export record in DB
6. Return `StageResult` with file_path and record_count

Export API routes:
- `GET /api/jobs/{id}/exports` — list exports
- `GET /api/exports/{id}/download` — file download (FileResponse)
- `GET /api/exports/{id}/card` — dataset card

```bash
git commit -m "feat: add Shipper export stage with JSON/JSONL/CSV and dataset cards"
```

---

## Stage 7: Orchestrator (Pipeline Coordinator)

### Task 20: Pipeline orchestrator

**Files:**
- Create: `backend/src/pipeline/orchestrator.py`
- Test: `backend/tests/test_pipeline/test_orchestrator.py`

The Orchestrator:
1. Receives job from Redis queue
2. Loads job config from DB
3. Runs stages sequentially: Spider → Refiner → Factory → Inspector → Shipper
4. Updates job status + stage + progress in DB after each stage
5. Publishes progress updates via Redis Pub/Sub (`pipeline:progress:{job_id}`)
6. On failure: stores error, marks job as "failed", preserves partial results
7. On success: marks job as "completed", stores total cost

```bash
git commit -m "feat: add pipeline orchestrator with sequential stage execution"
```

---

### Task 21: Worker entry point

**Files:**
- Create: `backend/src/worker.py`
- Test: manual (start worker, enqueue job, verify execution)

The worker process:
1. Initializes DB, logging, Redis
2. Runs infinite loop: `dequeue_job()` → `orchestrator.run(job)`
3. Handles graceful shutdown on SIGTERM/SIGINT
4. Runs as separate process (Docker container or `python -m src.worker`)

```bash
git commit -m "feat: add worker entry point for pipeline processing"
```

---

### Task 22: SSE streaming endpoint

**Files:**
- Create: `backend/src/api/routes/stream.py`
- Modify: `backend/src/main.py` — register stream router
- Test: `backend/tests/test_api/test_stream.py`

SSE endpoint `GET /api/jobs/{id}/stream`:
1. Subscribe to Redis Pub/Sub channel `pipeline:progress:{job_id}`
2. Stream events as SSE: `data: {"stage": "spider", "progress": 0.45, "message": "Scraping 3/7 URLs"}`
3. Close stream when job completes or client disconnects
4. Include keep-alive pings every 15 seconds

```bash
git commit -m "feat: add SSE streaming endpoint for real-time job progress"
```

---

### Task 23: Stats and templates API routes

**Files:**
- Create: `backend/src/api/routes/stats.py`
- Create: `backend/src/api/routes/templates.py`
- Modify: `backend/src/main.py` — register routers
- Test: `backend/tests/test_api/test_stats.py`

Stats routes:
- `GET /api/stats/overview` — aggregate counts from DB
- `GET /api/stats/costs` — cost breakdown by time period

Templates routes:
- `GET /api/templates` — list available template types
- `GET /api/templates/{type}` — template details + sample output

```bash
git commit -m "feat: add stats and templates API routes"
```

---

## Stage 8: Dashboard (JARVIS HUD UI)

### Task 24: Initialize Next.js frontend

**Files:**
- Create: `frontend/` — full Next.js 15 project
- Setup: Tailwind v4, ShadCN UI, JetBrains Mono + Inter fonts

```bash
cd frontend
npx create-next-app@latest . --typescript --tailwind --eslint --app --src-dir --no-import-alias
npx shadcn@latest init
```

Configure JARVIS design tokens:
- Background: `#0a0a0f`
- Primary accent: `#00d4ff` (Cyan)
- Warning/cost: `#ff8c00` (Orange)
- Success: `#00ff88`
- Glass effect: `rgba(255,255,255,0.05)` + `backdrop-blur-xl`
- Glow: `box-shadow: 0 0 20px rgba(0, 212, 255, 0.3)`

```bash
git commit -m "feat: initialize Next.js frontend with JARVIS design tokens"
```

---

### Task 25: API client + SSE hook

**Files:**
- Create: `frontend/src/lib/api.ts` — typed API client
- Create: `frontend/src/lib/types.ts` — TypeScript types matching backend schemas
- Create: `frontend/src/hooks/useSSE.ts` — SSE subscription hook
- Create: `frontend/src/hooks/useJobs.ts` — job management hook
- Create: `frontend/src/hooks/useProjects.ts` — project management hook

The API client wraps `fetch` with:
- Base URL configuration
- Error handling
- Type-safe request/response

The SSE hook:
- Connects to `/api/jobs/{id}/stream`
- Parses events and updates React state
- Auto-reconnects on disconnect
- Cleans up on unmount

```bash
git commit -m "feat: add frontend API client, types, and hooks"
```

---

### Task 26: Dashboard layout + home page

**Files:**
- Modify: `frontend/src/app/layout.tsx` — JARVIS theme, sidebar nav
- Modify: `frontend/src/app/page.tsx` — dashboard home
- Create: `frontend/src/components/dashboard/StatsOverview.tsx`
- Create: `frontend/src/components/dashboard/ActiveJobs.tsx`
- Create: `frontend/src/components/dashboard/RecentExports.tsx`
- Create: `frontend/src/components/dashboard/CostChart.tsx`
- Create: `frontend/src/components/ui/glass-panel.tsx` — reusable Glasmorphism panel
- Create: `frontend/src/components/ui/hud-border.tsx` — angular bracket borders

Build the dashboard home with:
- Sidebar navigation (glass panel, JARVIS-style)
- 4 stat cards (glass panels with glow)
- Active jobs section with progress bars
- Recent exports with download links
- Cost chart (Recharts bar chart)

```bash
git commit -m "feat: add JARVIS-style dashboard layout and home page"
```

---

### Task 27: Project management pages

**Files:**
- Create: `frontend/src/app/projects/page.tsx` — project list
- Create: `frontend/src/app/projects/[id]/page.tsx` — project detail
- Create: `frontend/src/app/projects/[id]/new-job/page.tsx` — new job form

The new-job page is the most complex frontend component:
- URL input textarea (one per line)
- Bulk file upload (txt/csv)
- Accordion config panels for each stage
- "Quick Start" preset (all defaults) vs "Custom"
- Cost estimation display
- Submit button that calls POST `/api/projects/{id}/jobs`

```bash
git commit -m "feat: add project management and job creation pages"
```

---

### Task 28: Job detail + pipeline visualizer

**Files:**
- Create: `frontend/src/app/jobs/[id]/page.tsx` — job detail
- Create: `frontend/src/app/jobs/[id]/results/page.tsx` — results + quality report
- Create: `frontend/src/components/dashboard/PipelineVisualizer.tsx` — animated pipeline
- Create: `frontend/src/components/dashboard/JobProgressCard.tsx`
- Create: `frontend/src/components/dashboard/QualityScoreChart.tsx`
- Create: `frontend/src/components/dashboard/CostTracker.tsx`

The PipelineVisualizer is the hero component:
- 5 stages as horizontal steps with icons
- Current stage has cyan glow + pulse animation
- Completed stages have green checkmark
- Animated particles/dots flowing between stages
- Progress bar per stage with item counter

SSE integration:
- useSSE hook subscribes to job stream
- Updates pipeline visualizer in real-time
- Shows live log messages

```bash
git commit -m "feat: add job detail pages with animated pipeline visualizer"
```

---

### Task 29: Exports + Settings pages

**Files:**
- Create: `frontend/src/app/exports/page.tsx` — download center
- Create: `frontend/src/app/settings/page.tsx` — API keys + defaults

Exports page: list all exports, download buttons, dataset card viewer.
Settings page: form for API keys (stored in backend), default pipeline config.

```bash
git commit -m "feat: add exports download center and settings page"
```

---

## Stage 9: Docker & Polish

### Task 30: Docker Compose setup

**Files:**
- Create: `docker-compose.yml`
- Create: `backend/Dockerfile`
- Create: `frontend/Dockerfile`

```yaml
# docker-compose.yml
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data

  backend-api:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=sqlite+aiosqlite:///db/factory.db
      - REDIS_URL=redis://redis:6379/0
    env_file:
      - .env
    volumes:
      - ./data:/app/data
      - ./db:/app/db
    depends_on:
      - redis

  worker:
    build:
      context: ./backend
      dockerfile: Dockerfile
    command: python -m src.worker
    environment:
      - DATABASE_URL=sqlite+aiosqlite:///db/factory.db
      - REDIS_URL=redis://redis:6379/0
    env_file:
      - .env
    volumes:
      - ./data:/app/data
      - ./db:/app/db
    depends_on:
      - redis

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000
    depends_on:
      - backend-api

volumes:
  redis-data:
```

Backend Dockerfile:
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[pipeline]"
RUN playwright install --with-deps chromium
COPY src/ src/
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Frontend Dockerfile:
```dockerfile
FROM node:22-alpine AS builder
WORKDIR /app
COPY package*.json .
RUN npm ci
COPY . .
RUN npm run build

FROM node:22-alpine
WORKDIR /app
COPY --from=builder /app/.next .next
COPY --from=builder /app/public public
COPY --from=builder /app/package*.json .
COPY --from=builder /app/node_modules node_modules
CMD ["npm", "start"]
```

**Test:** `docker compose up --build` → all 4 containers start, health check passes.

```bash
git commit -m "feat: add Docker Compose with 4-container setup"
```

---

### Task 31: README + final polish

**Files:**
- Create: `README.md` — setup guide, screenshots placeholder, architecture diagram
- Create: `CONTRIBUTING.md` — how to add new stages/templates
- Review: all error handling, logging, edge cases

README sections:
- Quick Start (`docker compose up`)
- Architecture diagram (text-based)
- API documentation link (Swagger UI at `/docs`)
- Configuration guide
- Adding custom templates
- v2 roadmap

```bash
git commit -m "docs: add README and CONTRIBUTING guide"
```

---

## Summary

| Stage | Tasks | Key Deliverable |
|---|---|---|
| 1. Foundation | Tasks 1-8 | FastAPI + DB + Redis + Config + Schemas + Project CRUD |
| 2. Spider | Tasks 9-13 | URL scraping with fallback, rate limiting, robots.txt |
| 3. Refiner | Task 14 | Content extraction, chunking, dedup |
| 4. Factory | Tasks 15-17 | LLM client, template system, generation stage |
| 5. Inspector | Task 18 | Quality checkers (toxicity, readability, format, dupes) |
| 6. Shipper | Task 19 | JSON/JSONL/CSV export with dataset cards |
| 7. Orchestrator | Tasks 20-23 | End-to-end coordination, worker, SSE, stats API |
| 8. Dashboard | Tasks 24-29 | JARVIS HUD UI with all pages |
| 9. Docker | Tasks 30-31 | Docker Compose, README, polish |

**Total: 31 tasks across 9 stages.**
