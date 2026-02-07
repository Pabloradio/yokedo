# app/core/errors.py

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Optional


class DomainError(Exception):
    """
    Base class for domain-level errors.

    Why it exists:
    - Domain code (engines) must not depend on HTTP concepts.
    - Routers translate DomainError -> HTTP responses.
    - Typed errors are safer than ValueError("...") strings.
    """


@dataclass(frozen=True)
class NotFoundError(DomainError):
    resource: str
    resource_id: uuid.UUID
    message: Optional[str] = None

    def __str__(self) -> str:
        return self.message or f"{self.resource} not found"


@dataclass(frozen=True)
class ForbiddenError(DomainError):
    resource: str
    resource_id: uuid.UUID
    message: Optional[str] = None

    def __str__(self) -> str:
        return self.message or f"{self.resource} access forbidden"


@dataclass(frozen=True)
class InvalidTimeRangeError(DomainError):
    message: str

    def __str__(self) -> str:
        return self.message


@dataclass(frozen=True)
class OverlapConflictError(DomainError):
    resource: str
    message: str
    conflicting_id: Optional[uuid.UUID] = None

    def __str__(self) -> str:
        return self.message
