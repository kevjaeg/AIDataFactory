"""Export API routes: list exports, download files, get dataset cards."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas import ExportResponse
from db.database import get_session
from db.models import Export

router = APIRouter(tags=["exports"])


@router.get("/api/jobs/{job_id}/exports", response_model=list[ExportResponse])
async def list_exports(
    job_id: int,
    session: AsyncSession = Depends(get_session),
) -> list[Export]:
    """List all exports for a given job."""
    result = await session.execute(
        select(Export).where(Export.job_id == job_id).order_by(Export.created_at.desc())
    )
    return list(result.scalars().all())


@router.get("/api/exports/{export_id}/download")
async def download_export(
    export_id: int,
    session: AsyncSession = Depends(get_session),
) -> FileResponse:
    """Download the exported dataset file."""
    export = await session.get(Export, export_id)
    if not export:
        raise HTTPException(status_code=404, detail="Export not found")

    file_path = Path(export.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Export file not found on disk")

    return FileResponse(
        path=str(file_path),
        filename=file_path.name,
        media_type="application/octet-stream",
    )


@router.get("/api/exports/{export_id}/card")
async def get_dataset_card(
    export_id: int,
    session: AsyncSession = Depends(get_session),
) -> PlainTextResponse:
    """Return the dataset card as Markdown text."""
    export = await session.get(Export, export_id)
    if not export:
        raise HTTPException(status_code=404, detail="Export not found")

    if not export.dataset_card:
        raise HTTPException(status_code=404, detail="Dataset card not available")

    return PlainTextResponse(content=export.dataset_card, media_type="text/markdown")
