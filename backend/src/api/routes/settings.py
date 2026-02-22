"""Settings API: expose current configuration (with secrets masked)."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from config import get_settings

router = APIRouter(tags=["settings"])


class SettingsResponse(BaseModel):
    # API keys (masked)
    openai_api_key_configured: bool
    huggingface_token_configured: bool

    # Generation
    generation_model: str
    generation_max_concurrent: int
    generation_examples_per_chunk: int

    # Quality
    quality_min_score: float
    quality_checks: list[str]

    # Processing
    processing_chunk_size: int
    processing_chunk_strategy: str
    processing_chunk_overlap: int

    # Scraping
    scraping_max_concurrent: int
    scraping_rate_limit: float

    # Export
    export_format: str


@router.get("/api/settings", response_model=SettingsResponse)
async def get_current_settings() -> SettingsResponse:
    """Return current server configuration with sensitive values masked."""
    settings = get_settings()
    return SettingsResponse(
        openai_api_key_configured=bool(settings.openai_api_key and settings.openai_api_key != "sk-your-key-here"),
        huggingface_token_configured=bool(settings.huggingface_token and settings.huggingface_token != "hf_your-token-here"),
        generation_model=settings.generation_model,
        generation_max_concurrent=settings.generation_max_concurrent,
        generation_examples_per_chunk=settings.generation_examples_per_chunk,
        quality_min_score=settings.quality_min_score,
        quality_checks=settings.quality_checks,
        processing_chunk_size=settings.processing_chunk_size,
        processing_chunk_strategy=settings.processing_chunk_strategy,
        processing_chunk_overlap=settings.processing_chunk_overlap,
        scraping_max_concurrent=settings.scraping_max_concurrent,
        scraping_rate_limit=settings.scraping_rate_limit,
        export_format=settings.export_format,
    )
