from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import text

from app.models.base import Base


if TYPE_CHECKING:
    from app.models.invitation_acceptances import InvitationAcceptance


class InvitationLink(Base):
    __tablename__ = "invitation_links"

    __table_args__ = (
        CheckConstraint(
            "max_uses IN (1, 5, 10, 25, 50)",
            name="max_uses_allowed",
        ),
        CheckConstraint(
            "current_uses >= 0",
            name="current_uses_non_negative",
        ),
        CheckConstraint(
            "current_uses <= max_uses",
            name="current_uses_lte_max_uses",
        ),
        CheckConstraint(
            "link_status IN ('active', 'expired', 'revoked', 'exhausted')",
            name="status_allowed",
        ),
        CheckConstraint(
            "expires_at > created_at",
            name="expires_after_created",
        ),
        Index("ix_invitation_links_creator_id", "creator_id"),
        Index("ix_invitation_links_status_expires_at", "link_status", "expires_at"),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    creator_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    token: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
    )
    max_uses: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    current_uses: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
    )
    link_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default=text("'active'"),
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    revoked_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    acceptances: Mapped[list["InvitationAcceptance"]] = relationship(
        back_populates="invitation_link",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )