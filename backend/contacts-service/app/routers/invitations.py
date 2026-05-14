from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
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
from app.database import get_db
from app.schemas.invitations import (
    AcceptInvitationLinkRequest,
    AcceptInvitationLinkResponse,
    CreateInvitationLinkRequest,
    CreateInvitationLinkResponse,
)
from app.services.invitation_service import (
    accept_invitation_link,
    create_invitation_link,
)

router = APIRouter(prefix="/invitations", tags=["invitations"])


def _parse_user_id_header(x_user_id: str) -> UUID:
    try:
        return UUID(x_user_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid X-User-ID header",
        ) from exc


@router.post(
    "",
    response_model=CreateInvitationLinkResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_invitation_link_endpoint(
    payload: CreateInvitationLinkRequest,
    x_user_id: str = Header(..., alias="X-User-ID"),
    session: AsyncSession = Depends(get_db),
) -> CreateInvitationLinkResponse:
    creator_user_id = _parse_user_id_header(x_user_id)

    try:
        async with session.begin():
            result = await create_invitation_link(
                session,
                creator_user_id=creator_user_id,
                max_uses=payload.max_uses,
                expires_in_days=payload.expires_in_days,
            )
    except InvalidInvitationMaxUsesError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid max_uses for invitation link",
        ) from exc
    except InvalidInvitationExpirationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid invitation expiration",
        ) from exc

    return CreateInvitationLinkResponse.model_validate(result)


@router.post(
    "/accept",
    response_model=AcceptInvitationLinkResponse,
    status_code=status.HTTP_200_OK,
)
async def accept_invitation_link_endpoint(
    payload: AcceptInvitationLinkRequest,
    x_user_id: str = Header(..., alias="X-User-ID"),
    session: AsyncSession = Depends(get_db),
) -> AcceptInvitationLinkResponse:
    invitation_recipient_user_id = _parse_user_id_header(x_user_id)

    try:
        async with session.begin():
            result = await accept_invitation_link(
                session,
                token=payload.token,
                invitation_recipient_user_id=invitation_recipient_user_id,
                accepted_via=payload.accepted_via,
            )
    except InvitationLinkNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation link not found",
        ) from exc
    except InvalidInvitationAcceptedViaError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid accepted_via value",
        ) from exc
    except SelfInvitationAcceptanceError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Users cannot accept their own invitation links",
        ) from exc
    except InvitationLinkExpiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Invitation link has expired",
        ) from exc
    except InvitationLinkRevokedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Invitation link has been revoked",
        ) from exc
    except InvitationLinkExhaustedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Invitation link has no remaining uses",
        ) from exc

    return AcceptInvitationLinkResponse.model_validate(result)