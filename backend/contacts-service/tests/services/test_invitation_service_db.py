# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false

from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest
from sqlalchemy import select

from app.core.domain_exceptions import (
    InvitationLinkExhaustedError,
    InvitationLinkExpiredError,
    InvitationLinkRevokedError,
)
from app.models.contact_events import ContactEvent
from app.models.contacts import Contact
from app.models.invitation_acceptances import InvitationAcceptance
from app.models.invitation_links import InvitationLink
from app.services.invitation_service import (
    accept_invitation_link,
    create_invitation_link,
)

# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false

@pytest.mark.asyncio
async def test_create_invitation_link_persists_link(
    db_session,
) -> None:
    creator_user_id = UUID("11111111-2222-3333-4444-555555555555")

    result = await create_invitation_link(
        db_session,
        creator_user_id=creator_user_id,
        max_uses=1,
        expires_in_days=30,
    )

    stored_result = await db_session.execute(
        select(InvitationLink).where(
            InvitationLink.id == result.invitation_link_id,
        )
    )
    stored_link = stored_result.scalar_one()

    assert stored_link.creator_id == creator_user_id
    assert stored_link.max_uses == 1
    assert stored_link.current_uses == 0
    assert stored_link.link_status == "active"
    assert stored_link.token == result.token


@pytest.mark.asyncio
async def test_accept_invitation_link_creates_contact_acceptance_and_event(
    db_session,
) -> None:
    creator_user_id = UUID("11111111-2222-3333-4444-555555555555")
    recipient_user_id = UUID("99439ad5-bbab-4ebe-9322-73cc220008bc")

    invitation_result = await create_invitation_link(
        db_session,
        creator_user_id=creator_user_id,
        max_uses=1,
        expires_in_days=30,
    )

    accept_result = await accept_invitation_link(
        db_session,
        token=invitation_result.token,
        invitation_recipient_user_id=recipient_user_id,
        accepted_via="web",
    )

    assert accept_result.status == "accepted"
    assert accept_result.contact_id is not None
    assert accept_result.creator_id == creator_user_id
    assert accept_result.invitation_recipient_user_id == recipient_user_id
    assert accept_result.current_uses == 1
    assert accept_result.max_uses == 1
    assert accept_result.link_status == "exhausted"

    contact_result = await db_session.execute(
        select(Contact).where(
            Contact.id == accept_result.contact_id,
        )
    )
    contact = contact_result.scalar_one()

    assert contact.current_status == "active"
    assert contact.initial_connection_source == "invitation_link"

    acceptance_result = await db_session.execute(
        select(InvitationAcceptance).where(
            InvitationAcceptance.invitation_link_id
            == invitation_result.invitation_link_id,
            InvitationAcceptance.user_id == recipient_user_id,
        )
    )
    acceptance = acceptance_result.scalar_one()

    assert acceptance.accepted_via == "web"

    event_result = await db_session.execute(
        select(ContactEvent).where(
            ContactEvent.contact_id == accept_result.contact_id,
        )
    )
    event = event_result.scalar_one()

    assert event.event_type == "connected"
    assert event.actor_user_id == recipient_user_id
    assert event.source == "invitation_link_acceptance"


@pytest.mark.asyncio
async def test_accept_invitation_link_rejects_expired_link(
    db_session,
):
    creator_user_id = UUID("11111111-2222-3333-4444-555555555555")
    recipient_user_id = UUID("99439ad5-bbab-4ebe-9322-73cc220008bc")

    invitation_result = await create_invitation_link(
        db_session,
        creator_user_id=creator_user_id,
        max_uses=1,
        expires_in_days=30,
    )

    invitation_link_result = await db_session.execute(
        select(InvitationLink).where(
            InvitationLink.id
            == invitation_result.invitation_link_id,
        )
    )

    invitation_link = invitation_link_result.scalar_one()

    invitation_link.created_at = datetime.now(timezone.utc) - timedelta(days=2)
    invitation_link.updated_at = invitation_link.created_at
    invitation_link.expires_at = datetime.now(timezone.utc) - timedelta(days=1)

    await db_session.flush()

    with pytest.raises(InvitationLinkExpiredError):
        await accept_invitation_link(
            db_session,
            token=invitation_result.token,
            invitation_recipient_user_id=recipient_user_id,
            accepted_via="web",
        )


@pytest.mark.asyncio
async def test_accept_invitation_link_rejects_revoked_link(
    db_session,
) -> None:
    creator_user_id = UUID("11111111-2222-3333-4444-555555555555")
    recipient_user_id = UUID("99439ad5-bbab-4ebe-9322-73cc220008bc")

    invitation_result = await create_invitation_link(
        db_session,
        creator_user_id=creator_user_id,
        max_uses=1,
        expires_in_days=30,
    )

    invitation_link_result = await db_session.execute(
        select(InvitationLink).where(
            InvitationLink.id == invitation_result.invitation_link_id,
        )
    )
    invitation_link = invitation_link_result.scalar_one()

    invitation_link.link_status = "revoked"
    invitation_link.revoked_at = datetime.now(timezone.utc)
    invitation_link.revoked_by = creator_user_id

    await db_session.flush()

    with pytest.raises(InvitationLinkRevokedError):
        await accept_invitation_link(
            db_session,
            token=invitation_result.token,
            invitation_recipient_user_id=recipient_user_id,
            accepted_via="web",
        )


@pytest.mark.asyncio
async def test_accept_invitation_link_rejects_exhausted_link(
    db_session,
) -> None:
    creator_user_id = UUID("11111111-2222-3333-4444-555555555555")
    recipient_user_id = UUID("99439ad5-bbab-4ebe-9322-73cc220008bc")

    invitation_result = await create_invitation_link(
        db_session,
        creator_user_id=creator_user_id,
        max_uses=1,
        expires_in_days=30,
    )

    invitation_link_result = await db_session.execute(
        select(InvitationLink).where(
            InvitationLink.id == invitation_result.invitation_link_id,
        )
    )
    invitation_link = invitation_link_result.scalar_one()

    invitation_link.link_status = "exhausted"
    invitation_link.current_uses = invitation_link.max_uses

    await db_session.flush()

    with pytest.raises(InvitationLinkExhaustedError):
        await accept_invitation_link(
            db_session,
            token=invitation_result.token,
            invitation_recipient_user_id=recipient_user_id,
            accepted_via="web",
        )


@pytest.mark.asyncio
async def test_accept_invitation_link_is_idempotent_for_same_user(
    db_session,
) -> None:
    creator_user_id = UUID("11111111-2222-3333-4444-555555555555")
    recipient_user_id = UUID("99439ad5-bbab-4ebe-9322-73cc220008bc")

    invitation_result = await create_invitation_link(
        db_session,
        creator_user_id=creator_user_id,
        max_uses=5,
        expires_in_days=30,
    )

    first_accept_result = await accept_invitation_link(
        db_session,
        token=invitation_result.token,
        invitation_recipient_user_id=recipient_user_id,
        accepted_via="web",
    )

    second_accept_result = await accept_invitation_link(
        db_session,
        token=invitation_result.token,
        invitation_recipient_user_id=recipient_user_id,
        accepted_via="web",
    )

    assert first_accept_result.status == "accepted"
    assert second_accept_result.status == "already_accepted"
    assert second_accept_result.contact_id == first_accept_result.contact_id
    assert second_accept_result.current_uses == 1

    contacts_result = await db_session.execute(
        select(Contact).where(
            Contact.id == first_accept_result.contact_id,
        )
    )
    contacts = contacts_result.scalars().all()

    assert len(contacts) == 1

    acceptances_result = await db_session.execute(
        select(InvitationAcceptance).where(
            InvitationAcceptance.invitation_link_id
            == invitation_result.invitation_link_id,
            InvitationAcceptance.user_id == recipient_user_id,
        )
    )
    acceptances = acceptances_result.scalars().all()

    assert len(acceptances) == 1

    events_result = await db_session.execute(
        select(ContactEvent).where(
            ContactEvent.contact_id == first_accept_result.contact_id,
        )
    )
    events = events_result.scalars().all()

    assert len(events) == 1


