from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, CheckConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ContactRequest(Base):
    __tablename__ = "contact_requests"

    # --- Identifiers ---
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    requester_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )

    requested_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )

    # --- State ---
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
    )

    # --- Optional fields ---
    message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    source: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )

    # --- Audit ---
    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=datetime.utcnow,
    )

    updated_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    responded_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
    )

    responded_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )

    # --- Constraints ---
    __table_args__ = (
        CheckConstraint(
            "requester_id != requested_id",
            name="ck_contact_requests_no_self_request",
        ),
        CheckConstraint(
            "status IN ('pending', 'accepted', 'rejected', 'cancelled')",
            name="ck_contact_requests_status_valid",
        ),
        Index(
            "idx_contact_requests_requested_status",
            "requested_id",
            "status",
        ),
        Index(
            "idx_contact_requests_requester_status",
            "requester_id",
            "status",
        ),
    )