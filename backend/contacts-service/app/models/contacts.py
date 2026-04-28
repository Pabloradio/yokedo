# app/models/contacts.py

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.contact_events import ContactEvent

class ContactCurrentStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class ContactInitialConnectionSource(Enum):
    CONTACT_REQUEST = "contact_request"
    INVITATION_LINK = "invitation_link"


class Contact(Base):
    __tablename__ = "contacts"

    __table_args__ = (
        UniqueConstraint(
            "user_low_id",
            "user_high_id",
            name="ux_contacts_user_low_id_user_high_id",
        ),
        CheckConstraint(
            "user_low_id < user_high_id",
            name="user_low_id_lt_user_high_id",
        ),
        CheckConstraint(
            "current_status IN ('active', 'inactive')",
            name="current_status",
        ),
        CheckConstraint(
            "initial_connection_source IN ('contact_request', 'invitation_link')",
            name="initial_connection_source",
        ),
        CheckConstraint(
            """
            (
                current_status = 'active'
                AND disconnected_at IS NULL
            )
            OR
            (
                current_status = 'inactive'
                AND disconnected_at IS NOT NULL
                AND disconnected_at >= connected_at
            )
            """,
            name="status_timestamp_consistency",
        ),
        Index(
            "ix_contacts_user_low_id",
            "user_low_id",
        ),
        Index(
            "ix_contacts_user_high_id",
            "user_high_id",
        ),
        Index(
            "ix_contacts_current_status",
            "current_status",
        ),
        Index(
            "ix_contacts_current_status_user_low_id",
            "current_status",
            "user_low_id",
        ),
        Index(
            "ix_contacts_current_status_user_high_id",
            "current_status",
            "user_high_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        nullable=False,
        server_default=text("gen_random_uuid()"),
    )

    user_low_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )

    user_high_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )

    current_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    initial_connection_source: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    connected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    disconnected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    events: Mapped[list["ContactEvent"]] = relationship(
        back_populates="contact",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )