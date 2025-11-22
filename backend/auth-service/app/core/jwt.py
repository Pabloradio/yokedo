from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import jwt

from app.core.settings import settings


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a signed JWT access token.

    Args:
        data: Payload to encode inside the token (e.g. {"sub": user_id}).
        expires_delta: Optional timedelta for explicit expiration.

    Returns:
        Encoded JWT as a string.
    """
    to_encode = data.copy()

    if expires_delta is None:
        expires_delta = timedelta(
            minutes=settings.access_token_expire_minutes
        )

    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    return encoded_jwt


def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate a JWT access token.

    Args:
        token: The JWT string received from the client.

    Returns:
        The decoded payload as a dictionary.

    Raises:
        jwt.PyJWTError: If the token is invalid or expired.
    """
    payload = jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
    )
    return payload
