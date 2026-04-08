# app/models/contact_events.py

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.contacts import Contact

class ContactEventType(Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"


class ContactEventSource(Enum):
    CONTACT_REQUEST_ACCEPTANCE = "contact_request_acceptance"
    INVITATION_LINK_ACCEPTANCE = "invitation_link_acceptance"
    MANUAL_DISCONNECT = "manual_disconnect"
    MANUAL_RECONNECT = "manual_reconnect"


class ContactEvent(Base):
    __tablename__ = "contact_events"

    __table_args__ = (
        CheckConstraint(
            "event_type IN ('connected', 'disconnected')",
            name="event_type",
        ),
        CheckConstraint(
            """
            source IN (
                'contact_request_acceptance',
                'invitation_link_acceptance',
                'manual_disconnect',
                'manual_reconnect'
            )
            """,
            name="source",
        ),
        CheckConstraint(
            """
            (
                event_type = 'connected'
                AND source IN (
                    'contact_request_acceptance',
                    'invitation_link_acceptance',
                    'manual_reconnect'
                )
            )
            OR
            (
                event_type = 'disconnected'
                AND source = 'manual_disconnect'
            )
            """,
            name="event_type_source_consistency",
        ),
        Index(
            "ix_contact_events_contact_id",
            "contact_id",
        ),
        Index(
            "ix_contact_events_event_at",
            "event_at",
        ),
        Index(
            "ix_contact_events_contact_id_event_at",
            "contact_id",
            "event_at",
        ),
        Index(
            "ix_contact_events_actor_user_id",
            "actor_user_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        nullable=False,
        server_default=text("gen_random_uuid()"),
    )

    contact_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("contacts.id", ondelete="CASCADE"),
        nullable=False,
    )

    event_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    event_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    actor_user_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    source: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    contact: Mapped["Contact"] = relationship(
        back_populates="events",
    )