# app/routers/weekly_templates.py

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_async_session
from app.core.errors import (
    ForbiddenError,
    InvalidTimeRangeError,
    NotFoundError,
    OverlapConflictError,
)
from app.services.availability_engine import (
    AvailabilityEngine,
    WeeklyTemplateSlotCreate,
    WeeklyTemplateSlotUpdate,
)


router = APIRouter(prefix="/weekly-templates", tags=["weekly-templates"])


class WeeklyTemplateSlotCreateIn(BaseModel):
    user_id: uuid.UUID  # MVP: will come from auth later
    weekday: int = Field(..., ge=1, le=7)
    start_minute: int = Field(..., ge=0, le=1439)
    end_minute: int = Field(..., ge=1, le=1440)
    timezone: str = Field(..., min_length=1, max_length=50)

    plan_text: Optional[str] = None
    language_code: str = Field(default="es", max_length=5)



class WeeklyTemplateSlotUpdateIn(BaseModel):
    user_id: uuid.UUID  # MVP: will come from auth later
    weekday: Optional[int] = Field(default=None, ge=1, le=7)
    start_minute: Optional[int] = Field(default=None, ge=0, le=1439)
    end_minute: Optional[int] = Field(default=None, ge=1, le=1440)
    timezone: Optional[str] = Field(default=None, min_length=1, max_length=50)

    plan_text: Optional[str] = None
    language_code: Optional[str] = Field(default=None, max_length=5)


class WeeklyTemplateSlotOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    weekday: int
    start_minute: int
    end_minute: int
    timezone: str
    plan_text: Optional[str]
    language_code: str
   
    class Config:
        from_attributes = True


def _raise_http_from_domain_error(err: Exception) -> None:
    # Domain -> HTTP mapping (single place, to keep routers thin)
    if isinstance(err, NotFoundError):
        raise HTTPException(status_code=404, detail=str(err))
    if isinstance(err, ForbiddenError):
        raise HTTPException(status_code=403, detail=str(err))
    if isinstance(err, InvalidTimeRangeError):
        raise HTTPException(status_code=400, detail=str(err))
    if isinstance(err, OverlapConflictError):
        raise HTTPException(status_code=409, detail=str(err))

    # Unexpected error type -> surface as 500 (keeps bugs visible in dev)
    raise HTTPException(status_code=500, detail="internal server error")


@router.post("", response_model=WeeklyTemplateSlotOut)
async def create_weekly_template_slot(
    payload: WeeklyTemplateSlotCreateIn,
    session: AsyncSession = Depends(get_async_session),
) -> WeeklyTemplateSlotOut:
    engine = AvailabilityEngine()
    try:
        created = await engine.create_weekly_template_slot(
            session=session,
            payload=WeeklyTemplateSlotCreate(
                user_id=payload.user_id,
                weekday=payload.weekday,
                start_minute=payload.start_minute,
                end_minute=payload.end_minute,
                timezone=payload.timezone,
                plan_text=payload.plan_text,
                language_code=payload.language_code,
            ),
        )
    except Exception as e:
        _raise_http_from_domain_error(e)

    return WeeklyTemplateSlotOut.model_validate(created)


@router.patch("/{template_id}", response_model=WeeklyTemplateSlotOut)
async def update_weekly_template_slot(
    template_id: uuid.UUID,
    payload: WeeklyTemplateSlotUpdateIn,
    session: AsyncSession = Depends(get_async_session),
) -> WeeklyTemplateSlotOut:
    engine = AvailabilityEngine()
    try:
        updated = await engine.update_weekly_template_slot(
            session=session,
            user_id=payload.user_id,  # MVP: will come from auth later
            template_id=template_id,
            payload=WeeklyTemplateSlotUpdate(
                weekday=payload.weekday,
                start_minute=payload.start_minute,
                end_minute=payload.end_minute,
                timezone=payload.timezone,
                plan_text=payload.plan_text,
                language_code=payload.language_code,
            ),
        )
    except Exception as e:
        _raise_http_from_domain_error(e)

    return WeeklyTemplateSlotOut.model_validate(updated)


@router.delete("/{template_id}", response_model=WeeklyTemplateSlotOut)
async def delete_weekly_template_slot(
    template_id: uuid.UUID,
    user_id: uuid.UUID,  # MVP: will come from auth later
    session: AsyncSession = Depends(get_async_session),
) -> WeeklyTemplateSlotOut:
    engine = AvailabilityEngine()
    try:
        deleted = await engine.delete_weekly_template_slot(
            session=session,
            user_id=user_id,
            template_id=template_id,
        )
    except Exception as e:
        _raise_http_from_domain_error(e)

    return WeeklyTemplateSlotOut.model_validate(deleted)
