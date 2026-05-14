# contacts-service/app/schemas/invitations.py

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CreateInvitationLinkRequest(BaseModel):
    max_uses: int = Field(
        description="Maximum number of effective invitation uses.",
    )
    expires_in_days: int = Field(
        description="Number of days until the invitation link expires.",
    )


class CreateInvitationLinkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    invitation_link_id: UUID
    token: str
    creator_id: UUID
    max_uses: int
    current_uses: int
    link_status: str
    expires_at: datetime
    created_at: datetime


class AcceptInvitationLinkRequest(BaseModel):
    token: str = Field(
        min_length=1,
        description="Invitation link token.",
    )
    accepted_via: Literal["web", "email", "link"]


class AcceptInvitationLinkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    status: Literal[
        "accepted",
        "reactivated",
        "already_accepted",
        "already_connected",
    ]
    invitation_link_id: UUID
    contact_id: UUID | None
    creator_id: UUID
    invitation_recipient_user_id: UUID
    current_uses: int
    max_uses: int
    link_status: str