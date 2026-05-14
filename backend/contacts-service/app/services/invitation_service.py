# contacts-service/app/services/invitation_service.py

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Literal
from uuid import UUID
import secrets

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.domain_exceptions import (
    InvalidInvitationAcceptedViaError,
    InvalidInvitationExpirationError,
    InvalidInvitationMaxUsesError,
    InvitationLinkExhaustedError,
    InvitationLinkExpiredError,
    InvitationLinkNotFoundError,
    InvitationLinkRevokedError,
    SelfInvitationAcceptanceError,
)

from app.core.postgres_concurrency import (
    acquire_transaction_advisory_lock,
    build_contact_pair_lock_key,
    build_invitation_link_lock_key,
    configure_transaction_timeouts,
)
from app.models.contact_events import ContactEvent
from app.models.contacts import Contact
from app.models.invitation_acceptances import InvitationAcceptance
from app.models.invitation_links import InvitationLink

from sqlalchemy import select



ALLOWED_INVITATION_MAX_USES = {1, 5, 10, 25, 50}
ALLOWED_ACCEPTED_VIA = {"web", "email", "link"}


AcceptInvitationLinkStatus = Literal[
    "accepted",
    "reactivated",
    "already_accepted",
    "already_connected",
]


@dataclass(frozen=True)
class CreateInvitationLinkResult:
    invitation_link_id: UUID
    token: str
    creator_id: UUID
    max_uses: int
    current_uses: int
    link_status: str
    expires_at: datetime
    created_at: datetime


@dataclass(frozen=True)
class AcceptInvitationLinkResult:
    status: AcceptInvitationLinkStatus
    invitation_link_id: UUID
    contact_id: UUID | None
    creator_id: UUID
    invitation_recipient_user_id: UUID
    current_uses: int
    max_uses: int
    link_status: str


def _generate_invitation_token() -> str:
    """Generate a URL-safe invitation token."""
    return secrets.token_urlsafe(32)


def _build_canonical_user_pair(user_a_id: UUID, user_b_id: UUID) -> tuple[UUID, UUID]:
    """Return a deterministic user pair matching contacts.user_low_id/user_high_id."""
    if user_a_id < user_b_id:
        return user_a_id, user_b_id

    return user_b_id, user_a_id


async def _get_contact_between_users(
    session: AsyncSession,
    *,
    user_a_id: UUID,
    user_b_id: UUID,
) -> Contact | None:
    """Return the contact row between two users, if it exists."""
    user_low_id, user_high_id = _build_canonical_user_pair(
        user_a_id,
        user_b_id,
    )

    result = await session.execute(
        select(Contact).where(
            Contact.user_low_id == user_low_id,
            Contact.user_high_id == user_high_id,
        )
    )

    return result.scalar_one_or_none()


async def create_invitation_link(
    session: AsyncSession,
    *,
    creator_user_id: UUID,
    max_uses: int,
    expires_in_days: int,
) -> CreateInvitationLinkResult:
    """Create a new invitation link owned by the given user. 
    The caller must execute this function inside an active transaction."""
    if max_uses not in ALLOWED_INVITATION_MAX_USES:
        raise InvalidInvitationMaxUsesError

    if expires_in_days <= 0:
        raise InvalidInvitationExpirationError

    now = datetime.now(timezone.utc)
    invitation_link = InvitationLink(
        creator_id=creator_user_id,
        token=_generate_invitation_token(),
        max_uses=max_uses,
        expires_at=now + timedelta(days=expires_in_days),
    )

    session.add(invitation_link)
    await session.flush()
  
    return CreateInvitationLinkResult(
        invitation_link_id=invitation_link.id,
        token=invitation_link.token,
        creator_id=invitation_link.creator_id,
        max_uses=invitation_link.max_uses,
        current_uses=invitation_link.current_uses,
        link_status=invitation_link.link_status,
        expires_at=invitation_link.expires_at,
        created_at=invitation_link.created_at,
    )


async def accept_invitation_link(
    session: AsyncSession,
    *,
    token: str,
    invitation_recipient_user_id: UUID,
    accepted_via: str,
) -> AcceptInvitationLinkResult:
    """Accept an invitation link and connect the recipient with the creator.
    The caller must execute this function inside an active transaction."""
    if accepted_via not in ALLOWED_ACCEPTED_VIA:
        raise InvalidInvitationAcceptedViaError

    result = await session.execute(
        select(InvitationLink).where(InvitationLink.token == token)
    )
    invitation_link = result.scalar_one_or_none()

    if invitation_link is None:
        raise InvitationLinkNotFoundError

    await configure_transaction_timeouts(session)
    
    await acquire_transaction_advisory_lock(
        session,
        build_invitation_link_lock_key(invitation_link.id),
    )

    result = await session.execute(
        select(InvitationLink).where(InvitationLink.id == invitation_link.id)
    )
    invitation_link = result.scalar_one()

    if invitation_link.creator_id == invitation_recipient_user_id:
        raise SelfInvitationAcceptanceError

    existing_acceptance_result = await session.execute(
        select(InvitationAcceptance).where(
            InvitationAcceptance.invitation_link_id == invitation_link.id,
            InvitationAcceptance.user_id == invitation_recipient_user_id,
        )
    )
    existing_acceptance = existing_acceptance_result.scalar_one_or_none()

    if existing_acceptance is not None:
        return AcceptInvitationLinkResult(
            status="already_accepted",
            invitation_link_id=invitation_link.id,
            contact_id=None,
            creator_id=invitation_link.creator_id,
            invitation_recipient_user_id=invitation_recipient_user_id,
            current_uses=invitation_link.current_uses,
            max_uses=invitation_link.max_uses,
            link_status=invitation_link.link_status,
        )

    now = datetime.now(timezone.utc)

    if invitation_link.expires_at <= now:
        if invitation_link.link_status == "active":
            invitation_link.link_status = "expired"
            invitation_link.updated_at = now

        raise InvitationLinkExpiredError

    if invitation_link.link_status == "revoked":
        raise InvitationLinkRevokedError

    if invitation_link.link_status == "exhausted":
        raise InvitationLinkExhaustedError

    await acquire_transaction_advisory_lock(
        session,
        build_contact_pair_lock_key(
            invitation_link.creator_id,
            invitation_recipient_user_id,
        ),
    )

    contact = await _get_contact_between_users(
        session,
        user_a_id=invitation_link.creator_id,
        user_b_id=invitation_recipient_user_id,
    )

    if contact is not None and contact.current_status == "active":
        return AcceptInvitationLinkResult(
            status="already_connected",
            invitation_link_id=invitation_link.id,
            contact_id=contact.id,
            creator_id=invitation_link.creator_id,
            invitation_recipient_user_id=invitation_recipient_user_id,
            current_uses=invitation_link.current_uses,
            max_uses=invitation_link.max_uses,
            link_status=invitation_link.link_status,
        )

    if invitation_link.current_uses >= invitation_link.max_uses:
        if invitation_link.link_status == "active":
            invitation_link.link_status = "exhausted"
            invitation_link.updated_at = now

        raise InvitationLinkExhaustedError

    user_low_id, user_high_id = _build_canonical_user_pair(
        invitation_link.creator_id,
        invitation_recipient_user_id,
    )

    if contact is None:
        contact = Contact(
            user_low_id=user_low_id,
            user_high_id=user_high_id,
            current_status="active",
            initial_connection_source="invitation_link",
            connected_at=now,
            disconnected_at=None,
            updated_at=now,
        )
        session.add(contact)
        result_status: AcceptInvitationLinkStatus = "accepted"
    else:
        contact.current_status = "active"
        contact.connected_at = now
        contact.disconnected_at = None
        contact.updated_at = now
        result_status = "reactivated"

    await session.flush()

    acceptance = InvitationAcceptance(
        invitation_link_id=invitation_link.id,
        user_id=invitation_recipient_user_id,
        accepted_via=accepted_via,
        accepted_at=now,
    )
    session.add(acceptance)

    contact_event = ContactEvent(
        contact_id=contact.id,
        event_type="connected",
        event_at=now,
        actor_user_id=invitation_recipient_user_id,
        source="invitation_link_acceptance",
    )
    session.add(contact_event)

    invitation_link.current_uses += 1
    invitation_link.updated_at = now

    if invitation_link.current_uses >= invitation_link.max_uses:
        invitation_link.link_status = "exhausted"

    await session.flush()

    return AcceptInvitationLinkResult(
        status=result_status,
        invitation_link_id=invitation_link.id,
        contact_id=contact.id,
        creator_id=invitation_link.creator_id,
        invitation_recipient_user_id=invitation_recipient_user_id,
        current_uses=invitation_link.current_uses,
        max_uses=invitation_link.max_uses,
        link_status=invitation_link.link_status,
    )