"""Templates API routes for listing available prompt templates."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from templates import TemplateRegistry

router = APIRouter(tags=["templates"])


@router.get("/api/templates")
async def list_templates() -> list[dict]:
    """List all available prompt template types."""
    names = TemplateRegistry.list_templates()
    result = []
    for name in names:
        template = TemplateRegistry.get(name)
        result.append({
            "name": name,
            "template_type": template.template_type,
            "has_system_prompt": bool(template.system_prompt),
        })
    return result


@router.get("/api/templates/{template_type}")
async def get_template_detail(template_type: str) -> dict:
    """Get details for a specific template type."""
    try:
        template = TemplateRegistry.get(template_type)
    except (KeyError, ValueError):
        raise HTTPException(status_code=404, detail=f"Template '{template_type}' not found")

    return {
        "name": template_type,
        "template_type": template.template_type,
        "system_prompt": template.system_prompt,
        "output_schema": template.output_schema,
    }
