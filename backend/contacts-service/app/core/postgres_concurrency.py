from __future__ import annotations

import hashlib
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def configure_transaction_timeouts(session: AsyncSession) -> None:
    """Set local PostgreSQL timeouts for the current transaction."""
    await session.execute(text("SET LOCAL lock_timeout = '3s'"))
    await session.execute(text("SET LOCAL statement_timeout = '10s'"))
    await session.execute(text("SET LOCAL idle_in_transaction_session_timeout = '15s'"))


def build_advisory_lock_key(namespace: str, value: str) -> int:
    """Build a deterministic signed 64-bit advisory lock key."""
    digest = hashlib.blake2b(
        f"{namespace}:{value}".encode("utf-8"),
        digest_size=8,
    ).digest()

    return int.from_bytes(
        digest,
        byteorder="big",
        signed=True,
    )


def build_invitation_link_lock_key(invitation_link_id: UUID) -> int:
    """Build the advisory lock key for one invitation link."""
    return build_advisory_lock_key(
        namespace="contacts.invitation_link",
        value=str(invitation_link_id),
    )


def build_contact_pair_lock_key(user_a_id: UUID, user_b_id: UUID) -> int:
    """Build the advisory lock key for a canonical user pair."""
    first_user_id, second_user_id = sorted((str(user_a_id), str(user_b_id)))

    return build_advisory_lock_key(
        namespace="contacts.contact_pair",
        value=f"{first_user_id}:{second_user_id}",
    )


async def acquire_transaction_advisory_lock(
    session: AsyncSession,
    lock_key: int,
) -> None:
    """Acquire a transaction-scoped PostgreSQL advisory lock."""
    await session.execute(
        text("SELECT pg_advisory_xact_lock(:lock_key)"),
        {"lock_key": lock_key},
    )