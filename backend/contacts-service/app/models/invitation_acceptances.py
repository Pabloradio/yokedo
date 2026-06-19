# contacts-service/app/models/invitation_acceptances.py

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import text

from app.models.base import Base


if TYPE_CHECKING:
    from app.models.invitation_links import InvitationLink


class InvitationAcceptance(Base):
    __tablename__ = "invitation_acceptances"

    __table_args__ = (
        CheckConstraint(
            "accepted_via IN ('web', 'email', 'link')",
            name="accepted_via_allowed",
        ),
        UniqueConstraint(
            "invitation_link_id",
            "user_id",
            name="ux_invitation_acceptances_link_user",
        ),
        Index(
            "ix_invitation_acceptances_invitation_link_id",
            "invitation_link_id",
        ),
        Index(
            "ix_invitation_acceptances_user_id",
            "user_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    invitation_link_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("invitation_links.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    accepted_via: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
    )
    accepted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    invitation_link: Mapped["InvitationLink"] = relationship(
        back_populates="acceptances",
    )