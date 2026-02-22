"""Tests for custom template CRUD API."""

import pytest
from httpx import AsyncClient

from templates import TemplateRegistry


VALID_TEMPLATE = {
    "name": "my-custom-qa",
    "template_type": "qa",
    "system_prompt": "You are a helpful assistant.",
    "user_prompt_template": "Generate QA pairs from: {{ content }}",
    "output_schema": {"type": "array", "items": {"type": "object"}},
}


@pytest.fixture(autouse=True)
def _clean_registry():
    """Remove custom templates from the in-memory registry between tests."""
    yield
    TemplateRegistry._custom_instances.clear()


async def test_create_custom_template(client: AsyncClient) -> None:
    """Create a custom template and verify response."""
    response = await client.post("/api/custom-templates", json=VALID_TEMPLATE)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "my-custom-qa"
    assert data["template_type"] == "qa"
    assert data["system_prompt"] == "You are a helpful assistant."
    assert data["id"] is not None
    assert data["created_at"] is not None


async def test_list_custom_templates(client: AsyncClient) -> None:
    """List returns created templates."""
    await client.post("/api/custom-templates", json=VALID_TEMPLATE)
    await client.post("/api/custom-templates", json={
        **VALID_TEMPLATE,
        "name": "another-template",
    })

    response = await client.get("/api/custom-templates")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2


async def test_get_custom_template(client: AsyncClient) -> None:
    """Get a single custom template by ID."""
    create = await client.post("/api/custom-templates", json=VALID_TEMPLATE)
    template_id = create.json()["id"]

    response = await client.get(f"/api/custom-templates/{template_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "my-custom-qa"


async def test_get_nonexistent_template(client: AsyncClient) -> None:
    """Get non-existent template returns 404."""
    response = await client.get("/api/custom-templates/99999")
    assert response.status_code == 404


async def test_update_custom_template(client: AsyncClient) -> None:
    """Update a custom template's fields."""
    create = await client.post("/api/custom-templates", json=VALID_TEMPLATE)
    template_id = create.json()["id"]

    response = await client.put(
        f"/api/custom-templates/{template_id}",
        json={"system_prompt": "Updated system prompt"},
    )
    assert response.status_code == 200
    assert response.json()["system_prompt"] == "Updated system prompt"
    # Other fields unchanged
    assert response.json()["name"] == "my-custom-qa"


async def test_delete_custom_template(client: AsyncClient) -> None:
    """Delete a custom template."""
    create = await client.post("/api/custom-templates", json=VALID_TEMPLATE)
    template_id = create.json()["id"]

    response = await client.delete(f"/api/custom-templates/{template_id}")
    assert response.status_code == 204

    # Verify deleted
    response = await client.get(f"/api/custom-templates/{template_id}")
    assert response.status_code == 404


async def test_duplicate_name_rejected(client: AsyncClient) -> None:
    """Creating template with duplicate name returns 409."""
    await client.post("/api/custom-templates", json=VALID_TEMPLATE)
    response = await client.post("/api/custom-templates", json=VALID_TEMPLATE)
    assert response.status_code == 409


async def test_invalid_jinja2_rejected(client: AsyncClient) -> None:
    """Creating template with invalid Jinja2 syntax returns 422."""
    bad_template = {
        **VALID_TEMPLATE,
        "name": "bad-jinja",
        "user_prompt_template": "{% if unclosed",
    }
    response = await client.post("/api/custom-templates", json=bad_template)
    assert response.status_code == 422


async def test_template_appears_in_registry(client: AsyncClient) -> None:
    """Created custom templates should appear in the template registry list."""
    await client.post("/api/custom-templates", json=VALID_TEMPLATE)

    # The built-in /api/templates endpoint lists from the registry
    response = await client.get("/api/templates")
    assert response.status_code == 200
    names = [t["name"] for t in response.json()]
    assert "my-custom-qa" in names
