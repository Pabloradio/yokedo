# app/routers/debug_availability.py

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_async_session
from app.services.availability_engine import (
    AvailabilityEngine, 
    PunctualAvailabilityCreate, 
    PunctualAvailabilityUpdate,
)


router = APIRouter(prefix="/debug/availabilities", tags=["debug"])


class PunctualAvailabilityIn(BaseModel):
    user_id: uuid.UUID
    start_time_utc: datetime
    end_time_utc: datetime
    timezone: str = Field(..., min_length=1, max_length=50)

    plan_text: Optional[str] = None
    language_code: str = Field(default="es", max_length=5)

    is_flexible: bool = False
    category_id: Optional[int] = None

    @field_validator("start_time_utc", "end_time_utc")
    @classmethod
    def must_be_timezone_aware(cls, v: datetime) -> datetime:
        if v.tzinfo is None or v.utcoffset() is None:
            raise ValueError("Datetime must be timezone-aware (e.g. 2026-01-30T10:00:00+00:00).")
        return v



class PunctualAvailabilityUpdateIn(BaseModel):
    user_id: uuid.UUID  # debug-only; real API will get this from the token
    start_time_utc: datetime
    end_time_utc: datetime
    timezone: str = Field(..., min_length=1, max_length=50)

    plan_text: Optional[str] = None
    language_code: str = Field(default="es", max_length=5)

    is_flexible: bool = False
    category_id: Optional[int] = None

    @field_validator("start_time_utc", "end_time_utc")
    @classmethod
    def must_be_timezone_aware(cls, v: datetime) -> datetime:
        if v.tzinfo is None or v.utcoffset() is None:
            raise ValueError("Datetime must be timezone-aware (e.g. 2026-01-30T10:00:00+00:00).")
        return v



class AvailabilityOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    start_time_utc: datetime
    end_time_utc: datetime
    timezone: str
    plan_text: Optional[str]
    language_code: str
    is_flexible: bool
    is_synthetic: bool
    source: Optional[str]
    is_recurring: bool
    category_id: Optional[int]

    class Config:
        from_attributes = True


@router.post("/punctual", response_model=AvailabilityOut)
async def create_or_replace_punctual(
    payload: PunctualAvailabilityIn,
    session: AsyncSession = Depends(get_async_session),
) -> AvailabilityOut:
    engine = AvailabilityEngine()

    created = await engine.create_punctual_with_overlap_replacement(
        session=session,
        payload=PunctualAvailabilityCreate(**payload.model_dump()),
    )
    return AvailabilityOut.model_validate(created)


@router.patch("/punctual/{availability_id}", response_model=AvailabilityOut)
async def update_punctual(
    availability_id: uuid.UUID,
    payload: PunctualAvailabilityUpdateIn,
    session: AsyncSession = Depends(get_async_session),
) -> AvailabilityOut:
    engine = AvailabilityEngine()
    updated = await engine.update_punctual_with_overlap_replacement(
        session=session,
        user_id=payload.user_id,  # debug-only; real API vendrá del token
        availability_id=availability_id,
        payload=PunctualAvailabilityUpdate(**payload.model_dump(exclude={"user_id"}, by_alias=False)),
    )
    return AvailabilityOut.model_validate(updated)