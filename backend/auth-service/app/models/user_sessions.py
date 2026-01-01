# app/models/session.py

import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import Base


class UserSession(Base):
    """
    Stores refresh token sessions for each user.
    Each record represents a single login session (device/browser).

    Why this table?
    - Supports secure refresh token rotation
    - Allows logout per device
    - Enables analytics (ML, behavior modeling)
    - Allows revocation of stolen/expired tokens
    - Prevents storing tokens in plaintext (we only store a hash)
    """

    __tablename__ = "user_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Link to the user who owns this session
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Hash of the refresh token (never store the original token)
    refresh_token_hash = Column(String(128), nullable=False)

    # Session creation time
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    # Session expiration time (e.g., 30 days)
    expires_at = Column(DateTime(timezone=True), nullable=False)

    # Optional but useful for analytics / MLOps
    user_agent = Column(String(200), nullable=True)     # Browser / device info
    ip_address = Column(String(45), nullable=True)      # IPv4/IPv6

    # Relationship for ORM convenience
    user = relationship("User", backref="sessions")

    def __repr__(self):
        return f"<Session {self.id} for user {self.user_id}>"
