# app/migrations/metadata.py

"""
Migration-only metadata for availability-service.

This module defines a standalone SQLAlchemy MetaData object used exclusively by Alembic
for schema autogeneration. It includes:

- Stub definitions for external tables (owned by other services) only to resolve FKs.
- Full definitions for availability-service owned tables.

Do not import this module from runtime application code.
"""

from sqlalchemy import (
    MetaData,
    Table,
    Column,
    Date,
    DateTime,
    Text,
    String,
    Boolean,
    Integer,
    SmallInteger,
    CheckConstraint,
    UniqueConstraint,
    ForeignKey,
    Index,
    text,
)
from sqlalchemy.dialects.postgresql import UUID


# Independent metadata used only for Alembic autogenerate
migration_metadata = MetaData()

# ---------------------------------------------------------------------
# External table stubs (owned by other services)
# ---------------------------------------------------------------------

# Owned by auth-service
users = Table(
    "users",
    migration_metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
)

# Owned by another domain (global schema)
plan_category = Table(
    "plan_category",
    migration_metadata,
    Column("id", Integer, primary_key=True),
)

# ---------------------------------------------------------------------
# Availability-service owned tables (schema v1.1 reference)
# ---------------------------------------------------------------------

availability_weekly_templates = Table(
    "availability_weekly_templates",
    migration_metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column(
        "user_id",
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("weekday", SmallInteger, nullable=False),
    Column("start_minute", SmallInteger, nullable=False),
    Column("end_minute", SmallInteger, nullable=False),
    Column("timezone", String(50), nullable=False),
    Column("plan_text", Text, nullable=True),
    Column(
        "language_code",
        String(5),
        nullable=False,
        server_default=text("'es'"),
    ),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=text("NOW()")),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=text("NOW()")),
    CheckConstraint("weekday BETWEEN 1 AND 7", name="ck_availability_weekly_templates_weekday_range"),
    CheckConstraint("start_minute BETWEEN 0 AND 1439", name="ck_availability_weekly_templates_start_minute_range"),
    CheckConstraint("end_minute BETWEEN 1 AND 1440", name="ck_availability_weekly_templates_end_minute_range"),
    CheckConstraint("start_minute < end_minute", name="ck_availability_weekly_templates_start_lt_end"),
    CheckConstraint(
        "language_code ~ '^[a-z]{2}(-[A-Z]{2})?$'",
        name="ck_availability_weekly_templates_language_code_format",
    ),
)

Index("idx_awd_user", availability_weekly_templates.c.user_id)
Index("idx_awd_user_weekday", availability_weekly_templates.c.user_id, availability_weekly_templates.c.weekday)


availability_day_overrides = Table(
    "availability_day_overrides",
    migration_metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column(
        "user_id",
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("date", Date, nullable=False),
    Column("timezone", String(50), nullable=False),
    Column("override_type", String(10), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=text("NOW()")),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=text("NOW()")),
    UniqueConstraint("user_id", "date", name="ux_availability_day_overrides_user_date"),
    CheckConstraint(
        "override_type IN ('replace','clear')",
        name="ck_availability_day_overrides_override_type",
    ),
)


availabilities = Table(
    "availabilities",
    migration_metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column(
        "user_id",
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("start_time_utc", DateTime(timezone=True), nullable=False),
    Column("end_time_utc", DateTime(timezone=True), nullable=False),
    Column("timezone", String(50), nullable=False),
    Column("plan_text", Text, nullable=True),
    Column(
        "language_code",
        String(5),
        nullable=True,
        server_default=text("'es'"),
    ),
    Column("is_flexible", Boolean, nullable=False, server_default=text("false")),
    Column("is_synthetic", Boolean, nullable=False, server_default=text("false")),
    Column("source", String, nullable=True),
    Column("is_recurring", Boolean, nullable=False, server_default=text("false")),
    Column(
        "category_id",
        Integer,
        ForeignKey("plan_category.id"),
        nullable=True,
    ),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=text("NOW()")),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=text("NOW()")),
    CheckConstraint("start_time_utc < end_time_utc", name="ck_availabilities_start_lt_end"),
    CheckConstraint(
        "language_code IS NULL OR language_code ~ '^[a-z]{2}(-[A-Z]{2})?$'",
        name="ck_availabilities_language_code_format",
    ),
    CheckConstraint(
        "source IS NULL OR source IN ('habitual','punctual')",
        name="ck_availabilities_source",
    ),
)

Index(
    "idx_availabilities_user_time",
    availabilities.c.user_id,
    availabilities.c.start_time_utc,
    availabilities.c.end_time_utc,
)
Index("idx_availabilities_timerange", availabilities.c.start_time_utc, availabilities.c.end_time_utc)
Index("idx_availabilities_synthetic", availabilities.c.is_synthetic)
Index(
    "idx_availabilities_plan_text",
    availabilities.c.plan_text,
    postgresql_where=availabilities.c.plan_text.isnot(None),
)
Index("idx_availabilities_category", availabilities.c.category_id)
Index(
    "idx_availabilities_source",
    availabilities.c.source,
    postgresql_where=availabilities.c.source.isnot(None),
)
