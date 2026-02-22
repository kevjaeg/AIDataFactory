"""Custom template CRUD API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from jinja2 import Environment, TemplateSyntaxError
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas import CustomTemplateCreate, CustomTemplateUpdate, CustomTemplateResponse
from db.database import get_session
from db.models import CustomTemplate
from templates import TemplateRegistry

router = APIRouter(tags=["custom-templates"])

_jinja_env = Environment()


def _validate_jinja2(template_str: str) -> None:
    """Validate Jinja2 syntax. Raises HTTPException on error."""
    try:
        _jinja_env.parse(template_str)
    except TemplateSyntaxError as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid Jinja2 syntax in user_prompt_template: {exc}",
        )


@router.get("/api/custom-templates", response_model=list[CustomTemplateResponse])
async def list_custom_templates(
    session: AsyncSession = Depends(get_session),
) -> list[CustomTemplate]:
    """List all custom templates."""
    result = await session.execute(
        select(CustomTemplate).order_by(CustomTemplate.name)
    )
    return list(result.scalars().all())


@router.get("/api/custom-templates/{template_id}", response_model=CustomTemplateResponse)
async def get_custom_template(
    template_id: int,
    session: AsyncSession = Depends(get_session),
) -> CustomTemplate:
    """Get a single custom template by ID."""
    template = await session.get(CustomTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Custom template not found")
    return template


@router.post("/api/custom-templates", status_code=201, response_model=CustomTemplateResponse)
async def create_custom_template(
    body: CustomTemplateCreate,
    session: AsyncSession = Depends(get_session),
) -> CustomTemplate:
    """Create a new custom template."""
    # Validate Jinja2 syntax
    _validate_jinja2(body.user_prompt_template)

    # Check name uniqueness
    existing = await session.execute(
        select(CustomTemplate).where(CustomTemplate.name == body.name)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"Template name '{body.name}' already exists")

    template = CustomTemplate(
        name=body.name,
        template_type=body.template_type,
        system_prompt=body.system_prompt,
        user_prompt_template=body.user_prompt_template,
        output_schema=body.output_schema,
    )
    session.add(template)
    await session.commit()
    await session.refresh(template)

    # Update in-memory registry
    TemplateRegistry.register_custom(template)
    logger.info(f"Created custom template: {template.name}")

    return template


@router.put("/api/custom-templates/{template_id}", response_model=CustomTemplateResponse)
async def update_custom_template(
    template_id: int,
    body: CustomTemplateUpdate,
    session: AsyncSession = Depends(get_session),
) -> CustomTemplate:
    """Update an existing custom template."""
    template = await session.get(CustomTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Custom template not found")

    update_data = body.model_dump(exclude_unset=True)

    # Validate Jinja2 if user_prompt_template is being updated
    if "user_prompt_template" in update_data:
        _validate_jinja2(update_data["user_prompt_template"])

    # Check name uniqueness if name is being updated
    if "name" in update_data and update_data["name"] != template.name:
        existing = await session.execute(
            select(CustomTemplate).where(CustomTemplate.name == update_data["name"])
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=409,
                detail=f"Template name '{update_data['name']}' already exists",
            )
        # Unregister old name from registry
        TemplateRegistry.unregister_custom(template.name)

    for key, value in update_data.items():
        setattr(template, key, value)

    await session.commit()
    await session.refresh(template)

    # Update in-memory registry
    TemplateRegistry.register_custom(template)
    logger.info(f"Updated custom template: {template.name}")

    return template


@router.delete("/api/custom-templates/{template_id}", status_code=204)
async def delete_custom_template(
    template_id: int,
    session: AsyncSession = Depends(get_session),
) -> None:
    """Delete a custom template."""
    template = await session.get(CustomTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Custom template not found")

    # Remove from in-memory registry
    TemplateRegistry.unregister_custom(template.name)

    await session.delete(template)
    await session.commit()
    logger.info(f"Deleted custom template: {template.name}")
