import pytest
from uuid import uuid4

from app.core.domain_exceptions import (
    InvalidInvitationAcceptedViaError,
    InvalidInvitationExpirationError,
    InvalidInvitationMaxUsesError,
)
from app.services.invitation_service import (
    accept_invitation_link,
    create_invitation_link,
)


@pytest.mark.asyncio
async def test_create_invitation_link_rejects_invalid_max_uses() -> None:
    with pytest.raises(InvalidInvitationMaxUsesError):
        await create_invitation_link(
            session=None,  # type: ignore[arg-type]
            creator_user_id=uuid4(),
            max_uses=2,
            expires_in_days=7,
        )


@pytest.mark.asyncio
async def test_create_invitation_link_rejects_invalid_expiration() -> None:
    with pytest.raises(InvalidInvitationExpirationError):
        await create_invitation_link(
            session=None,  # type: ignore[arg-type]
            creator_user_id=uuid4(),
            max_uses=1,
            expires_in_days=0,
        )


@pytest.mark.asyncio
async def test_accept_invitation_link_rejects_invalid_accepted_via() -> None:
    with pytest.raises(InvalidInvitationAcceptedViaError):
        await accept_invitation_link(
            session=None,  # type: ignore[arg-type]
            token="valid-looking-token",
            invitation_recipient_user_id=uuid4(),
            accepted_via="sms",
        )
        