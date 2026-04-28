# app/migrations/metadata.py

from sqlalchemy import Column, MetaData, Table
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from typing import cast

from app.models.base import NAMING_CONVENTION
from app.models.contact_requests import ContactRequest
from app.models.contacts import Contact
from app.models.contact_events import ContactEvent


migration_metadata = MetaData(naming_convention=NAMING_CONVENTION)

# Stub table for external dependency owned by auth-service.
# This table exists only so Alembic can resolve foreign keys during autogenerate.
Table(
    "users",
    migration_metadata,
    Column("id", PGUUID(as_uuid=True), primary_key=True, nullable=False),
)

cast(Table, ContactRequest.__table__).to_metadata(migration_metadata)
cast(Table, Contact.__table__).to_metadata(migration_metadata)
cast(Table, ContactEvent.__table__).to_metadata(migration_metadata)