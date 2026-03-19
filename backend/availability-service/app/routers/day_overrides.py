from __future__ import annotations

import uuid
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.availability_engine import AvailabilityEngine, DayOverrideSet

from app.core.dependencies import get_async_session
from app.core.errors import ForbiddenError, NotFoundError, NotFoundByKeyError


router = APIRouter(prefix="/day-overrides", tags=["day-overrides"])


class DayOverrideSetIn(BaseModel):
    user_id: uuid.UUID  # MVP: will come from auth later
    date: date  # local date in user's timezone
    timezone: str = Field(..., min_length=1, max_length=50)
    override_type: Literal["clear", "replace"]


class DayOverrideOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    date: date
    timezone: str
    override_type: str

    class Config:
        from_attributes = True


def _raise_http_from_domain_error(err: Exception) -> None:
    # Domain -> HTTP mapping (single place, to keep routers thin)
    if isinstance(err, NotFoundError):
        raise HTTPException(status_code=404, detail=str(err))
    if isinstance(err, ForbiddenError):
        raise HTTPException(status_code=403, detail=str(err))
    if isinstance(err, NotFoundByKeyError):
        raise HTTPException(status_code=404, detail=str(err))


    # Unexpected error type -> surface as 500 (keeps bugs visible in dev)
    raise HTTPException(status_code=500, detail="internal server error")


@router.put("", response_model=DayOverrideOut)
async def set_day_override(
    payload: DayOverrideSetIn,
    session: AsyncSession = Depends(get_async_session),
) -> DayOverrideOut:
    engine = AvailabilityEngine()
    try:
        row = await engine.set_day_override(
            session=session,
            payload=DayOverrideSet(
                user_id=payload.user_id,
                date=payload.date,
                timezone=payload.timezone,
                override_type=payload.override_type,
            ),
        )
    except Exception as e:
        _raise_http_from_domain_error(e)

    return DayOverrideOut.model_validate(row)


@router.get("", response_model=DayOverrideOut)
async def get_day_override(
    user_id: uuid.UUID,
    date: date,
    session: AsyncSession = Depends(get_async_session),
) -> DayOverrideOut:
    engine = AvailabilityEngine()
    try:
        row = await engine.get_day_override(
            session=session,
            user_id=user_id,
            date_=date,
        )
    except Exception as e:
        _raise_http_from_domain_error(e)

    return DayOverrideOut.model_validate(row)


@router.delete("", response_model=DayOverrideOut)
async def delete_day_override(
    user_id: uuid.UUID,
    date: date,
    session: AsyncSession = Depends(get_async_session),
) -> DayOverrideOut:
    engine = AvailabilityEngine()
    try:
        row = await engine.delete_day_override(
            session=session,
            user_id=user_id,
            date_=date,
        )
    except Exception as e:
        _raise_http_from_domain_error(e)

    return DayOverrideOut.model_validate(row)
