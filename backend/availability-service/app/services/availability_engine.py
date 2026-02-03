from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.availability import Availability


@dataclass(frozen=True)
class PunctualAvailabilityCreate:
    user_id: uuid.UUID
    start_time_utc: datetime
    end_time_utc: datetime
    timezone: str
    plan_text: Optional[str] = None
    language_code: str = "es"
    is_flexible: bool = False
    category_id: Optional[int] = None


@dataclass(frozen=True)
class PunctualAvailabilityUpdate:
    start_time_utc: datetime
    end_time_utc: datetime
    timezone: str
    plan_text: Optional[str] = None
    language_code: str = "es"
    is_flexible: bool = False
    category_id: Optional[int] = None


class AvailabilityEngine:
    """
    Domain service for availability operations.

    MVP policy:
    - Time ranges are interpreted as [start, end) (half-open interval).
    - If a new slot overlaps existing ones, we do NOT merge.
      We delete all overlapping slots ("aggressive delete") and then insert/update.
    - Concurrency: PostgreSQL advisory locks serialize writes per user_id.
    - IMPORTANT (MVP): `availabilities` stores ONLY punctual slots explicitly created by the user.
      Habitual rules live in `availability_weekly_templates` + `availability_day_overrides`.
    """

    async def create_punctual_with_overlap_replacement(
        self,
        session: AsyncSession,
        payload: PunctualAvailabilityCreate,
    ) -> Availability:
        _validate_range(payload.start_time_utc, payload.end_time_utc)

        async with session.begin():
            await _advisory_lock_user(session, payload.user_id)

            await self._delete_overlapping_punctual(
                session=session,
                user_id=payload.user_id,
                new_start=payload.start_time_utc,
                new_end=payload.end_time_utc,
                exclude_id=None,
            )

            new_row = Availability(
                user_id=payload.user_id,
                start_time_utc=payload.start_time_utc,
                end_time_utc=payload.end_time_utc,
                timezone=payload.timezone,
                plan_text=payload.plan_text,
                language_code=payload.language_code,
                is_flexible=payload.is_flexible,
                # MVP: always false for user-created punctual slots
                is_synthetic=False,
                # MVP: fixed
                source="punctual",
                is_recurring=False,
                category_id=payload.category_id,
            )
            session.add(new_row)
            await session.flush()
            await session.refresh(new_row)
            return new_row

    async def update_punctual_with_overlap_replacement(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        availability_id: uuid.UUID,
        payload: PunctualAvailabilityUpdate,
    ) -> Availability:
        _validate_range(payload.start_time_utc, payload.end_time_utc)

        async with session.begin():
            await _advisory_lock_user(session, user_id)

            # Load and check ownership + punctual-ness (MVP invariant).
            stmt = select(Availability).where(Availability.id == availability_id)
            row = (await session.execute(stmt)).scalar_one_or_none()
            if row is None:
                raise ValueError("availability not found")

            if row.user_id != user_id:
                raise ValueError("availability does not belong to user")

            if row.source != "punctual" or row.is_synthetic:
                raise ValueError("only non-synthetic punctual slots can be edited in MVP")

            await self._delete_overlapping_punctual(
                session=session,
                user_id=user_id,
                new_start=payload.start_time_utc,
                new_end=payload.end_time_utc,
                exclude_id=availability_id,
            )

            # Keep the same ID: UPDATE the existing row.
            row.start_time_utc = payload.start_time_utc
            row.end_time_utc = payload.end_time_utc
            row.timezone = payload.timezone
            row.plan_text = payload.plan_text
            row.language_code = payload.language_code
            row.is_flexible = payload.is_flexible
            row.category_id = payload.category_id

            await session.flush()
            await session.refresh(row)
            return row

    async def _delete_overlapping_punctual(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        new_start: datetime,
        new_end: datetime,
        exclude_id: uuid.UUID | None,
    ) -> None:
        delete_stmt = (
            delete(Availability)
            .where(Availability.user_id == user_id)
            # MVP safety: don't touch anything except punctual slots
            .where(Availability.source == "punctual")
            # MVP safety: don't touch synthetic rows (future-proof)
            .where(Availability.is_synthetic.is_(False))
            # Overlap test for [start, end)
            .where(Availability.start_time_utc < new_end)
            .where(Availability.end_time_utc > new_start)
        )

        if exclude_id is not None:
            delete_stmt = delete_stmt.where(Availability.id != exclude_id)

        await session.execute(delete_stmt)


def _validate_range(start: datetime, end: datetime) -> None:
    if start >= end:
        raise ValueError("start_time_utc must be < end_time_utc")


async def _advisory_lock_user(session: AsyncSession, user_id: uuid.UUID) -> None:
    lock_key = _uuid_to_pg_advisory_key(user_id)
    await session.execute(text("SELECT pg_advisory_xact_lock(:key)").bindparams(key=lock_key))


def _uuid_to_pg_advisory_key(value: uuid.UUID) -> int:
    raw = int.from_bytes(value.bytes[0:8], byteorder="big", signed=False)
    if raw >= 2**63:
        return raw - 2**64
    return raw - 0
