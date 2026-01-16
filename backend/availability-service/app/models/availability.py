# app/models/availability.py

from __future__ import annotations

import uuid
from datetime import date, datetime
from enum import Enum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class OverrideType(str, Enum):
    REPLACE = "replace"
    CLEAR = "clear"


class AvailabilitySource(str, Enum):
    HABITUAL = "habitual"
    PUNCTUAL = "punctual"


class AvailabilityWeeklyTemplate(Base):
    """
    Weekly template slots (habitual availability rules).
    They are not real calendar occurrences. Applied only when no day override exists.
    """

    __tablename__ = "availability_weekly_templates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ISO 8601: 1=Monday, 7=Sunday
    weekday: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    # Minutes since 00:00 (0..1439). end_minute in 1..1440.
    start_minute: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    end_minute: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    # IANA timezone, e.g. "Europe/Madrid"
    timezone: Mapped[str] = mapped_column(String(50), nullable=False)

    # Optional free text (stored here; embeddings later in ai-service)
    plan_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # e.g. "es", "en", "es-ES"
    language_code: Mapped[str] = mapped_column(String(5), server_default="es")

    # Optional structured category
    category_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("plan_category.id"), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint("weekday BETWEEN 1 AND 7", name="ck_awt_weekday_1_7"),
        CheckConstraint("start_minute BETWEEN 0 AND 1439", name="ck_awt_start_minute_range"),
        CheckConstraint("end_minute BETWEEN 1 AND 1440", name="ck_awt_end_minute_range"),
        CheckConstraint("start_minute < end_minute", name="ck_awt_start_lt_end"),
        Index("idx_awt_user_weekday", "user_id", "weekday"),
    )


class AvailabilityDayOverride(Base):
    """
    Explicit signal that a given local date does NOT follow the weekly template.
    Avoids ambiguity between "no punctual data" and "not available".
    """

    __tablename__ = "availability_day_overrides"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Local date in user's timezone
    date: Mapped[date] = mapped_column(Date, nullable=False)

    timezone: Mapped[str] = mapped_column(String(50), nullable=False)

    override_type: Mapped[str] = mapped_column(String(10), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint(
            "override_type IN ('replace','clear')",
            name="ck_ado_override_type",
        ),
        Index("idx_ado_user_date", "user_id", "date", unique=True),
    )


class Availability(Base):
    """
    Punctual slots stored in UTC. Used for:
    - daily/month views
    - matching
    In the MVP, availability-service should create these with source='punctual'.
    """

    __tablename__ = "availabilities"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    start_time_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    timezone: Mapped[str] = mapped_column(String, nullable=False)

    plan_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    language_code: Mapped[str] = mapped_column(String(5), server_default="es")

    is_flexible: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    is_synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")

    source: Mapped[str | None] = mapped_column(String, nullable=True)
    is_recurring: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")

    category_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("plan_category.id"), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint("start_time_utc < end_time_utc", name="ck_av_start_lt_end"),
        CheckConstraint(
            "language_code ~ '^[a-z]{2}(-[A-Z]{2})?$'",
            name="ck_av_language_code_format",
        ),
        CheckConstraint(
            "source IN ('habitual','punctual') OR source IS NULL",
            name="ck_av_source",
        ),
        Index("idx_availabilities_user_time", "user_id", "start_time_utc", "end_time_utc"),
        Index("idx_availabilities_timerange", "start_time_utc", "end_time_utc"),
        Index("idx_availabilities_synthetic", "is_synthetic"),
        Index("idx_availabilities_category", "category_id"),
    )
