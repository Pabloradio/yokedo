# app/core/refresh.py

import secrets
import hashlib
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from fastapi import HTTPException, status

from app.models.user_sessions import UserSession
from app.models.user import User
from app.database import async_session

# --------------------------------------------------------
# Helper: generate a cryptographically secure refresh token
# --------------------------------------------------------
def generate_refresh_token() -> str:
    """
    Generates a secure random refresh token.
    - Using secrets.token_hex(32) provides 64 hex characters (256-bit).
    - This is considered cryptographically secure for long-lived tokens.
    """
    return secrets.token_hex(32)


# --------------------------------------------------------
# Helper: hash the refresh token before storing it
# --------------------------------------------------------
def hash_refresh_token(token: str) -> str:
    """
    Hashes the refresh token using SHA256.

    We NEVER store the raw refresh token in the database.
    Storing the hash protects users if the database is compromised.

    SHA256(token) -> 64 hex chars.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


# --------------------------------------------------------
# Main function: create and store a refresh token session
# --------------------------------------------------------
async def create_refresh_token_session(user_id: str, user_agent: str | None, ip_address: str | None):
    """
    Creates a new refresh token session for the given user.

    Steps:
    1. Generate a secure refresh token
    2. Hash it for database storage
    3. Store the session with expiration (e.g., 30 days)
    4. Return the raw token (the hash stays in DB)

    The raw token is returned because the client must receive it.
    """
    raw_token = generate_refresh_token()
    token_hash = hash_refresh_token(raw_token)

    # Define expiration: 30 days (typical industry standard)
    expires_at = datetime.now(timezone.utc) + timedelta(days=30)

    async with async_session() as session:
        new_session = UserSession(
            user_id=user_id,
            refresh_token_hash = token_hash,
            created_at = datetime.now(timezone.utc),
            expires_at = expires_at,
            user_agent = user_agent,
            ip_address = ip_address
        )

        session.add(new_session)
        await session.commit()

    return raw_token  # The API returns this to the client


async def validate_refresh_token(refresh_token: str) -> UserSession:
    """
    Validate a provided refresh token by:
    - hashing it
    - matching it against stored sessions
    - checking expiration and user activity
    Returns the matching UserSession object if valid.
    """
    async with async_session() as session:
        
        # 1. Hash the provided refresh token (must match the stored one)
        token_hash = hashlib.sha256(refresh_token.encode("utf-8")).hexdigest()
        
        # 2. Look for a matching session
        query = select(UserSession).where(
            UserSession.refresh_token_hash == token_hash
        )
        result = await session.execute(query)
        stored_session = result.scalar_one_or_none()
        
        if stored_session is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        # 🚫 NEW: block refresh for soft-deleted accounts
        if user.is_deleted:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account has been deleted"
            )

        # 3. Check expiration
        now = datetime.now(timezone.utc)
        if stored_session.expires_at < now:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token expired"
            )
        
        # 4. Check user existence and activity
        user_result = await session.execute(
            select(User).where(User.id == stored_session.user_id)
        )
        user = user_result.scalar_one_or_none()
        
        if user is None or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User inactive or does not exist"
            )
        
        # Everything is valid → return the session
        return stored_session

