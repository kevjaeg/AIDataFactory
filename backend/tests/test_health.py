import pytest
from httpx import AsyncClient


async def test_health_returns_status(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "components" in data
    assert data["components"]["database"] in ("ok", "not_initialized")
