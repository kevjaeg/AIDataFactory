from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from config import get_settings
from logging_config import setup_logging
from db.database import init_db, close_db
from api.routes import health, projects, jobs, exports, stream, stats, templates_api


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
app.include_router(projects.router)
app.include_router(jobs.router)
app.include_router(exports.router)
app.include_router(stream.router)
app.include_router(stats.router)
app.include_router(templates_api.router)
