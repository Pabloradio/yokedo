from __future__ import annotations

from sqlalchemy import Column, Table
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from app.models.base import Base


users_stub = Table(
    "users",
    Base.metadata,
    Column("id", PGUUID(as_uuid=True), primary_key=True, nullable=False),
)