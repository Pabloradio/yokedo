# app/routers/availabilities.py

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession


from app.core.dependencies import get_async_session
from app.services.availability_engine import (
    AvailabilityEngine,
    PunctualAvailabilityCreate,
    PunctualAvailabilityUpdate
)



router = APIRouter(prefix="/availabilities", tags=["availabilities"])


class PunctualAvailabilityIn(BaseModel):
    user_id: uuid.UUID
    start_time_utc: datetime
    end_time_utc: datetime
    timezone: str = Field(..., min_length=1, max_length=50)

    plan_text: Optional[str] = None
    language_code: str = Field(default="es", max_length=5)

    is_flexible: bool = False
    is_synthetic: bool = False

    source: str = "punctual"
    is_recurring: bool = False

    category_id: Optional[int] = None

    @field_validator("start_time_utc", "end_time_utc")
    @classmethod
    def must_be_timezone_aware(cls, v: datetime) -> datetime:
        if v.tzinfo is None or v.utcoffset() is None:
            raise ValueError(
                "Datetime must be timezone-aware (e.g. 2026-01-30T10:00:00+00:00)."
            )
        return v


class PunctualAvailabilityUpdateIn(BaseModel):
    user_id: uuid.UUID = Field(
        ...,
        description="MVP (temporary): provided by client. Will be taken from auth token in a future iteration."
    )
    start_time_utc: Optional[datetime] = None
    end_time_utc: Optional[datetime] = None
    timezone: Optional[str] = Field(default=None, min_length=1, max_length=50)

    plan_text: Optional[str] = None
    language_code: Optional[str] = Field(default=None, max_length=5)

    is_flexible: Optional[bool] = None
    category_id: Optional[int] = None


    @field_validator("start_time_utc", "end_time_utc")
    @classmethod
    def must_be_timezone_aware_if_present(cls, v: Optional[datetime]) -> Optional[datetime]:
        if v is None:
            return v
        if v.tzinfo is None or v.utcoffset() is None:
            raise ValueError(
                "Datetime must be timezone-aware (e.g. 2026-01-30T10:00:00+00:00)."
            )
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
async def create_punctual(
    payload: PunctualAvailabilityIn,
    session: AsyncSession = Depends(get_async_session),
) -> AvailabilityOut:
    engine = AvailabilityEngine()
    created = await engine.create_punctual_with_overlap_replacement(
        session=session,
        payload=PunctualAvailabilityCreate(
            user_id=payload.user_id,
            start_time_utc=payload.start_time_utc,
            end_time_utc=payload.end_time_utc,
            timezone=payload.timezone,
            plan_text=payload.plan_text,
            language_code=payload.language_code,
            is_flexible=payload.is_flexible,
            category_id=payload.category_id,
        ),
    )

    return AvailabilityOut.model_validate(created)



@router.patch("/punctual/{availability_id}", response_model=AvailabilityOut)
async def update_punctual(
    availability_id: uuid.UUID,
    payload: PunctualAvailabilityUpdateIn,
    session: AsyncSession = Depends(get_async_session),
) -> AvailabilityOut:
    domain_payload = PunctualAvailabilityUpdate(
        start_time_utc=payload.start_time_utc,
        end_time_utc=payload.end_time_utc,
        timezone=payload.timezone,
        plan_text=payload.plan_text,
        language_code=payload.language_code,
        is_flexible=payload.is_flexible,
        category_id=payload.category_id,
    )

    engine = AvailabilityEngine()
    try:
        updated = await engine.update_punctual_with_overlap_replacement(
            session=session,
            user_id=payload.user_id,  # MVP: user_id comes from client input. Replace with authenticated user_id when auth integration is added.
            availability_id=availability_id,
            payload=domain_payload,
        )
    except ValueError as e:
        msg = str(e)

        if msg == "availability not found":
            raise HTTPException(status_code=404, detail=msg)
        if msg == "availability does not belong to user":
            raise HTTPException(status_code=403, detail=msg)
        if msg == "only non-synthetic punctual slots can be edited in MVP":
            raise HTTPException(status_code=403, detail=msg)
        if msg == "start_time_utc must be < end_time_utc":
            raise HTTPException(status_code=400, detail=msg)

        # Unknown ValueError -> keep it explicit (still a 500, but with a clear message)
        raise HTTPException(status_code=500, detail=msg)

    return AvailabilityOut.model_validate(updated)



