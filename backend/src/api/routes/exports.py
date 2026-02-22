"""Export API routes: list exports, download files, get dataset cards."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas import ExportResponse, HFPushRequest, HFPushResponse
from config import get_settings
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


@router.post("/api/exports/{export_id}/push-to-hf")
async def push_to_huggingface(
    export_id: int,
    body: HFPushRequest,
    session: AsyncSession = Depends(get_session),
) -> HFPushResponse:
    """Push an exported dataset to HuggingFace Hub."""
    export = await session.get(Export, export_id)
    if not export:
        raise HTTPException(status_code=404, detail="Export not found")

    file_path = Path(export.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Export file not found on disk")

    settings = get_settings()
    if not settings.huggingface_token:
        raise HTTPException(
            status_code=400,
            detail="HuggingFace token not configured. Set HUGGINGFACE_TOKEN in your environment.",
        )

    try:
        from clients.hf_client import HFClient
        client = HFClient(token=settings.huggingface_token)
        result = await client.push_dataset(
            file_path=file_path,
            repo_id=body.repo_id,
            private=body.private,
        )
        return HFPushResponse(**result)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to push to HuggingFace: {exc}")
