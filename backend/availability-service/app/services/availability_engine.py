# app/services/availability_engine.py

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy import delete, select, text, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from app.models.availability import (
    Availability,
    AvailabilityDayOverride,
)
from app.core.errors import (
    ForbiddenError,
    NotFoundError,
    InvalidTimeRangeError,
    OverlapConflictError,
    NotFoundByKeyError
)
from app.models.availability import AvailabilityWeeklyTemplate
from zoneinfo import ZoneInfo


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
    is_synthetic: bool = False


@dataclass(frozen=True)
class PunctualAvailabilityUpdate:
    start_time_utc: Optional[datetime] = None
    end_time_utc: Optional[datetime] = None
    timezone: Optional[str] = None
    plan_text: Optional[str] = None
    language_code: Optional[str] = None
    is_flexible: Optional[bool] = None
    category_id: Optional[int] = None


@dataclass(frozen=True)
class WeeklyTemplateSlotCreate:
    user_id: uuid.UUID
    weekday: int  # 1..7
    start_minute: int  # 0..1439
    end_minute: int  # 1..1440
    timezone: str
    plan_text: Optional[str] = None
    language_code: str = "es"


@dataclass(frozen=True)
class WeeklyTemplateSlotUpdate:
    weekday: Optional[int] = None
    start_minute: Optional[int] = None
    end_minute: Optional[int] = None
    timezone: Optional[str] = None
    plan_text: Optional[str] = None
    language_code: Optional[str] = None
    

@dataclass(frozen=True)
class DayOverrideSet:
    user_id: uuid.UUID
    date: date  # local date in user's timezone
    timezone: str
    override_type: str  # "clear" | "replace"


@dataclass(frozen=True)
class DayAvailabilityQuery:
    user_id: uuid.UUID
    date: date  # local date in query timezone
    timezone: str  # IANA timezone for "day" boundaries


@dataclass(frozen=True)
class AvailabilitySlot:
    start_time_utc: datetime
    end_time_utc: datetime
    timezone: str
    source: str  # "punctual" | "habitual"
    plan_text: Optional[str] = None
    language_code: str = "es"


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
        async with session.begin():
            await _advisory_lock_user(session, user_id)

            # Load and check ownership + punctual-ness (MVP invariant).
            stmt = select(Availability).where(Availability.id == availability_id)
            row = (await session.execute(stmt)).scalar_one_or_none()
            if row is None:
                raise NotFoundError(resource="availability", resource_id=availability_id)

            if row.user_id != user_id:
                raise ForbiddenError(resource="availability", resource_id=availability_id)

            if row.source != "punctual" or row.is_synthetic:
                raise ForbiddenError(
                    resource="availability",
                    resource_id=availability_id,
                    message="only non-synthetic punctual slots can be edited in MVP",
                )


            # --- MOD 1: compute the final time range (existing + patch) ---
            # PATCH may omit start/end, so we must validate using the final values.
            new_start = payload.start_time_utc if payload.start_time_utc is not None else row.start_time_utc
            new_end = payload.end_time_utc if payload.end_time_utc is not None else row.end_time_utc

            _validate_range(new_start, new_end)

            # --- MOD 2: only apply overlap replacement when time changes ---
            time_changed = (payload.start_time_utc is not None) or (payload.end_time_utc is not None)
            if time_changed:
                await self._delete_overlapping_punctual(
                    session=session,
                    user_id=user_id,
                    new_start=new_start,
                    new_end=new_end,
                    exclude_id=availability_id,
                )

            # --- MOD 3: patch semantics (only overwrite fields that are present) ---
            # Times: update to the computed final values (even if only one side changed).
            row.start_time_utc = new_start
            row.end_time_utc = new_end

            if payload.timezone is not None:
                row.timezone = payload.timezone
            if payload.plan_text is not None:
                row.plan_text = payload.plan_text
            if payload.language_code is not None:
                row.language_code = payload.language_code
            if payload.is_flexible is not None:
                row.is_flexible = payload.is_flexible
            if payload.category_id is not None:
                row.category_id = payload.category_id

            await session.flush()
            await session.refresh(row)
            return row

        
    async def delete_punctual(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        availability_id: uuid.UUID,
    ) -> Availability:
        async with session.begin():
            await _advisory_lock_user(session, user_id)

            stmt = select(Availability).where(Availability.id == availability_id)
            row = (await session.execute(stmt)).scalar_one_or_none()
            if row is None:
                raise NotFoundError(resource="availability", resource_id=availability_id)

            if row.user_id != user_id:
                raise ForbiddenError(resource="availability", resource_id=availability_id)

            # MVP safety: only user-created punctual slots can be deleted
            if row.source != "punctual" or row.is_synthetic:
                raise ForbiddenError(
                    resource="availability",
                    resource_id=availability_id,
                    message="only non-synthetic punctual slots can be deleted in MVP",
                )

            await session.delete(row)
            await session.flush()
            return row

    async def create_weekly_template_slot(
        self,
        session: AsyncSession,
        payload: WeeklyTemplateSlotCreate,
    ) -> AvailabilityWeeklyTemplate:
        _validate_weekly_template_range(
            weekday=payload.weekday,
            start_minute=payload.start_minute,
            end_minute=payload.end_minute,
        )

        async with session.begin():
            await _advisory_lock_user(session, payload.user_id)

            conflict_id = await _find_weekly_template_overlap(
                session=session,
                user_id=payload.user_id,
                weekday=payload.weekday,
                start_minute=payload.start_minute,
                end_minute=payload.end_minute,
                exclude_id=None,
            )
            if conflict_id is not None:
                raise OverlapConflictError(
                    resource="weekly_template_slot",
                    message="weekly template slot overlaps an existing slot",
                    conflicting_id=conflict_id,
                )

            row = AvailabilityWeeklyTemplate(
                user_id=payload.user_id,
                weekday=payload.weekday,
                start_minute=payload.start_minute,
                end_minute=payload.end_minute,
                timezone=payload.timezone,
                plan_text=payload.plan_text,
                language_code=payload.language_code,

            )
            session.add(row)
            await session.flush()
            await session.refresh(row)
            return row


    async def update_weekly_template_slot(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        template_id: uuid.UUID,
        payload: WeeklyTemplateSlotUpdate,
    ) -> AvailabilityWeeklyTemplate:
        async with session.begin():
            await _advisory_lock_user(session, user_id)

            stmt = select(AvailabilityWeeklyTemplate).where(
                AvailabilityWeeklyTemplate.id == template_id
            )
            row = (await session.execute(stmt)).scalar_one_or_none()
            if row is None:
                raise NotFoundError(resource="weekly_template_slot", resource_id=template_id)

            if row.user_id != user_id:
                raise ForbiddenError(resource="weekly_template_slot", resource_id=template_id)

            # Patch semantics: compute final values (existing + payload)
            new_weekday = payload.weekday if payload.weekday is not None else row.weekday
            new_start = (
                payload.start_minute if payload.start_minute is not None else row.start_minute
            )
            new_end = payload.end_minute if payload.end_minute is not None else row.end_minute

            _validate_weekly_template_range(
                weekday=new_weekday,
                start_minute=new_start,
                end_minute=new_end,
            )

            conflict_id = await _find_weekly_template_overlap(
                session=session,
                user_id=user_id,
                weekday=new_weekday,
                start_minute=new_start,
                end_minute=new_end,
                exclude_id=template_id,
            )
            if conflict_id is not None:
                raise OverlapConflictError(
                    resource="weekly_template_slot",
                    message="weekly template slot overlaps an existing slot",
                    conflicting_id=conflict_id,
                )

            # Apply patch
            row.weekday = new_weekday
            row.start_minute = new_start
            row.end_minute = new_end

            if payload.timezone is not None:
                row.timezone = payload.timezone
            if payload.plan_text is not None:
                row.plan_text = payload.plan_text
            if payload.language_code is not None:
                row.language_code = payload.language_code

            await session.flush()
            await session.refresh(row)
            return row


    async def delete_weekly_template_slot(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        template_id: uuid.UUID,
    ) -> AvailabilityWeeklyTemplate:
        async with session.begin():
            await _advisory_lock_user(session, user_id)

            stmt = select(AvailabilityWeeklyTemplate).where(
                AvailabilityWeeklyTemplate.id == template_id
            )
            row = (await session.execute(stmt)).scalar_one_or_none()
            if row is None:
                raise NotFoundError(resource="weekly_template_slot", resource_id=template_id)

            if row.user_id != user_id:
                raise ForbiddenError(resource="weekly_template_slot", resource_id=template_id)

            # Keep a copy in memory to return after deletion
            await session.delete(row)
            await session.flush()
            return row


    async def set_day_override(
        self,
        session: AsyncSession,
        payload: DayOverrideSet,
    ) -> AvailabilityDayOverride:
        """
        Upsert a single override per (user_id, local date).

        MVP semantics:
        - Both "clear" and "replace" disable weekly templates for that day in projection.
        - "replace" is kept for future semantics (special day definition).
        """
        async with session.begin():
            await _advisory_lock_user(session, payload.user_id)

            stmt = (
                insert(AvailabilityDayOverride)
                .values(
                    user_id=payload.user_id,
                    date=payload.date,
                    timezone=payload.timezone,
                    override_type=payload.override_type,
                )
                .on_conflict_do_update(
                    index_elements=[AvailabilityDayOverride.user_id, AvailabilityDayOverride.date],
                    set_={
                        "timezone": payload.timezone,
                        "override_type": payload.override_type,
                        "updated_at": func.now(),
                    },
                )
                .returning(AvailabilityDayOverride.id)
            )

            override_id = (await session.execute(stmt)).scalar_one()

            # Load ORM entity in the same transaction (guarantees it exists)
            row_stmt = select(AvailabilityDayOverride).where(AvailabilityDayOverride.id == override_id)
            row = (await session.execute(row_stmt)).scalar_one()

            # Refresh to ensure we return DB-populated timestamps
            await session.refresh(row)
            return row


    async def get_day_override(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        date_: date,
    ) -> AvailabilityDayOverride:
        async with session.begin():
            stmt = select(AvailabilityDayOverride).where(
                AvailabilityDayOverride.user_id == user_id,
                AvailabilityDayOverride.date == date_,
            )
            row = (await session.execute(stmt)).scalar_one_or_none()
            if row is None:
                raise NotFoundByKeyError(
                    resource="day_override",
                    key=f"user_id={user_id}, date={date_.isoformat()}",
                )

            return row

    async def delete_day_override(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        date_: date,
    ) -> AvailabilityDayOverride:
        async with session.begin():
            await _advisory_lock_user(session, user_id)

            stmt = select(AvailabilityDayOverride).where(
                AvailabilityDayOverride.user_id == user_id,
                AvailabilityDayOverride.date == date_,
            )
            row = (await session.execute(stmt)).scalar_one_or_none()
            if row is None:
                raise NotFoundByKeyError(
                    resource="day_override",
                    key=f"user_id={user_id}, date={date_.isoformat()}",
                )



            await session.delete(row)
            await session.flush()
            return row

    async def get_day_availability(
        self,
        session: AsyncSession,
        payload: DayAvailabilityQuery,
    ) -> list[AvailabilitySlot]:
        """
        Returns projected availability slots for a given local day (defined by payload.timezone).

        Composition (MVP):
        - Punctual slots from `availabilities` that overlap the day's UTC range.
        - Weekly template projection for that ISO weekday ONLY IF no day override exists for (user_id, date).
        """
        day_start_utc, day_end_utc = _local_day_to_utc_range(payload.date, payload.timezone)

        # --- 1) Punctual slots overlapping the day range ---
        punctual_stmt = (
            select(Availability)
            .where(Availability.user_id == payload.user_id)
            .where(Availability.source == "punctual")
            .where(Availability.is_synthetic.is_(False))
            .where(Availability.start_time_utc < day_end_utc)
            .where(Availability.end_time_utc > day_start_utc)
            .order_by(Availability.start_time_utc.asc())
        )
        punctual_rows = (await session.execute(punctual_stmt)).scalars().all()

        punctual_slots = [
            AvailabilitySlot(
                start_time_utc=row.start_time_utc,
                end_time_utc=row.end_time_utc,
                timezone=row.timezone,
                source="punctual",
                plan_text=row.plan_text,
                language_code=row.language_code,
            )
            for row in punctual_rows
        ]

        # --- 2) If a day override exists, habitual projection is disabled ---
        override_stmt = select(AvailabilityDayOverride.id).where(
            AvailabilityDayOverride.user_id == payload.user_id,
            AvailabilityDayOverride.date == payload.date,
        )
        override_exists = (await session.execute(override_stmt)).scalar_one_or_none() is not None
        if override_exists:
            return punctual_slots

        # --- 3) Weekly template projection for that weekday ---
        weekday = _iso_weekday_for_local_date(payload.date)

        templates_stmt = (
            select(AvailabilityWeeklyTemplate)
            .where(AvailabilityWeeklyTemplate.user_id == payload.user_id)
            .where(AvailabilityWeeklyTemplate.weekday == weekday)
            .order_by(AvailabilityWeeklyTemplate.start_minute.asc())
        )
        templates = (await session.execute(templates_stmt)).scalars().all()

        habitual_slots: list[AvailabilitySlot] = []
        for tpl in templates:
            # interpret template in its own timezone (Option A)
            tz = ZoneInfo(tpl.timezone)

            start_local = datetime(
                payload.date.year,
                payload.date.month,
                payload.date.day,
                0,
                0,
                0,
                tzinfo=tz,
            ) + timedelta(minutes=tpl.start_minute)

            end_local = datetime(
                payload.date.year,
                payload.date.month,
                payload.date.day,
                0,
                0,
                0,
                tzinfo=tz,
            ) + timedelta(minutes=tpl.end_minute)

            habitual_slots.append(
                AvailabilitySlot(
                    start_time_utc=start_local.astimezone(ZoneInfo("UTC")),
                    end_time_utc=end_local.astimezone(ZoneInfo("UTC")),
                    timezone=tpl.timezone,
                    source="habitual",
                    plan_text=tpl.plan_text,
                    language_code=tpl.language_code,
                )
            )

        # MVP: return both sets concatenated (no merging yet)
        return sorted(punctual_slots + habitual_slots, key=lambda s: s.start_time_utc)

    
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
        raise InvalidTimeRangeError("start_time_utc must be < end_time_utc")
    

def _validate_weekly_template_range(weekday: int, start_minute: int, end_minute: int) -> None:
    if weekday < 1 or weekday > 7:
        raise InvalidTimeRangeError("weekday must be in 1..7")

    if start_minute < 0 or start_minute > 1439:
        raise InvalidTimeRangeError("start_minute must be in 0..1439")

    if end_minute < 1 or end_minute > 1440:
        raise InvalidTimeRangeError("end_minute must be in 1..1440")

    if start_minute >= end_minute:
        raise InvalidTimeRangeError("start_minute must be < end_minute")


async def _find_weekly_template_overlap(
    session: AsyncSession,
    user_id: uuid.UUID,
    weekday: int,
    start_minute: int,
    end_minute: int,
    exclude_id: uuid.UUID | None,
) -> uuid.UUID | None:
    stmt = select(AvailabilityWeeklyTemplate.id).where(
        AvailabilityWeeklyTemplate.user_id == user_id,
        AvailabilityWeeklyTemplate.weekday == weekday,
        AvailabilityWeeklyTemplate.start_minute < end_minute,
        AvailabilityWeeklyTemplate.end_minute > start_minute,
    )
    if exclude_id is not None:
        stmt = stmt.where(AvailabilityWeeklyTemplate.id != exclude_id)

    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def _advisory_lock_user(session: AsyncSession, user_id: uuid.UUID) -> None:
    lock_key = _uuid_to_pg_advisory_key(user_id)
    await session.execute(text("SELECT pg_advisory_xact_lock(:key)").bindparams(key=lock_key))


def _uuid_to_pg_advisory_key(value: uuid.UUID) -> int:
    raw = int.from_bytes(value.bytes[0:8], byteorder="big", signed=False)
    if raw >= 2**63:
        return raw - 2**64
    return raw - 0


def _local_day_to_utc_range(day: date, tz_name: str) -> tuple[datetime, datetime]:
    """
    Convert a local date in tz_name to the UTC half-open range [start, end).
    Handles DST transitions correctly via zoneinfo.
    """
    tz = ZoneInfo(tz_name)
    local_start = datetime(day.year, day.month, day.day, 0, 0, 0, tzinfo=tz)
    local_end = datetime(day.year, day.month, day.day, 0, 0, 0, tzinfo=tz)  # placeholder
    # next day (safe across month/year boundaries)
    next_day = day.fromordinal(day.toordinal() + 1)
    local_end = datetime(next_day.year, next_day.month, next_day.day, 0, 0, 0, tzinfo=tz)

    return (local_start.astimezone(ZoneInfo("UTC")), local_end.astimezone(ZoneInfo("UTC")))


def _iso_weekday_for_local_date(day: date) -> int:
    # Python date.isoweekday(): Monday=1 .. Sunday=7
    return day.isoweekday()
