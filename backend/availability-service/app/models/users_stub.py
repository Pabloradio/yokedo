# app/models/users_stub.py

from __future__ import annotations

import uuid

from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class UserStub(Base):
    """
    ORM stub for an external table owned by another service (auth-service).

    Why it exists:
    - Availability models have FK(user_id) -> users.id
    - SQLAlchemy needs the referenced table to exist in the same MetaData
      to properly configure mappers and flush INSERTs.

    Important:
    - This model must NOT be migrated by availability-service Alembic.
    - It exists only for runtime FK resolution in the ORM.
    """

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
