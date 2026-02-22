from fastapi import APIRouter
from sqlalchemy import text

router = APIRouter()


@router.get("/health")
@router.get("/api/health")
async def health_check() -> dict:
    """Health check endpoint with component status."""
    from db.database import _engine

    checks: dict[str, str] = {}

    # Database check
    try:
        if _engine:
            async with _engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
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
