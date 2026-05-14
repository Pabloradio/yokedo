class DomainError(Exception):
    """Base class for domain-level errors."""


class InvitationDomainError(DomainError):
    """Base class for invitation-related domain errors."""


class InvitationLinkNotFoundError(InvitationDomainError):
    """Raised when an invitation link token does not exist."""


class InvitationLinkExpiredError(InvitationDomainError):
    """Raised when an invitation link has expired."""


class InvitationLinkRevokedError(InvitationDomainError):
    """Raised when an invitation link has been revoked."""


class InvitationLinkExhaustedError(InvitationDomainError):
    """Raised when an invitation link has no remaining effective uses."""


class InvalidInvitationMaxUsesError(InvitationDomainError):
    """Raised when max_uses is not allowed for invitation links."""


class InvalidInvitationExpirationError(InvitationDomainError):
    """Raised when expires_in_days is invalid."""


class InvalidInvitationAcceptedViaError(InvitationDomainError):
    """Raised when accepted_via is not an allowed value."""


class SelfInvitationAcceptanceError(InvitationDomainError):
    """Raised when a user tries to accept their own invitation link."""