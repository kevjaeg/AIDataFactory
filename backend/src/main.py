from fastapi import FastAPI

from config import get_settings
from logging_config import setup_logging

app = FastAPI(
    title="AI Data Factory",
    version="0.1.0",
    description="Production-grade AI training data pipeline",
)

# Setup logging on module load (will be moved to lifespan in Task 6)
_settings = get_settings()
setup_logging(level=_settings.log_level)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
