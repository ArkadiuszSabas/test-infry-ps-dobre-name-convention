"""Framework-free DocMind browser session domain models."""

from dataclasses import dataclass, field, replace
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from docmind_api.domain.auth.actors import AuthProvider


class SessionRevocationReason(StrEnum):
    """Audit-safe reason a browser session was revoked."""

    USER_LOGOUT = "user_logout"
    USER_REVOKED = "user_revoked"
    ADMIN_REVOKED = "admin_revoked"
    ACCOUNT_DISABLED = "account_disabled"
    PASSWORD_RESET = "password_reset"
    UNKNOWN = "unknown"


class UserSessionStatus(StrEnum):
    """Response-safe lifecycle status for a browser session."""

    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"


@dataclass(frozen=True, slots=True)
class SessionTokenHash:
    """Persisted hash of an opaque browser session token."""

    value: str = field(repr=False)

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise ValueError("Session token hash cannot be empty.")


@dataclass(frozen=True, slots=True)
class RefreshTokenHash:
    """Persisted hash of an opaque browser refresh token."""

    value: str = field(repr=False)

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise ValueError("Refresh token hash cannot be empty.")


@dataclass(frozen=True, slots=True)
class SessionClientFingerprint:
    """Privacy-preserving client fingerprint derived before persistence."""

    value: str = field(repr=False)

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise ValueError("Session client fingerprint cannot be empty.")


@dataclass(frozen=True, slots=True)
class SessionClientMetadata:
    """Safe browser/client metadata captured for session diagnostics."""

    client_label: str | None = None
    client_fingerprint: SessionClientFingerprint | None = None

    def __post_init__(self) -> None:
        if self.client_label is not None and not self.client_label.strip():
            raise ValueError("Session client label cannot be empty.")


@dataclass(frozen=True, slots=True)
class UserSession:
    """API-owned browser session for a DocMind user."""

    id: UUID
    user_id: UUID
    token_hash: SessionTokenHash = field(repr=False)
    created_at: datetime
    last_seen_at: datetime
    expires_at: datetime
    auth_provider: AuthProvider
    identity_link_id: UUID | None
    client_label: str | None = None
    client_fingerprint: SessionClientFingerprint | None = None
    revoked_at: datetime | None = None
    revoked_reason: SessionRevocationReason | None = None

    def __post_init__(self) -> None:
        if self.auth_provider == AuthProvider.LOCAL and self.identity_link_id is not None:
            raise ValueError("Local user sessions cannot reference an identity link.")
        if self.auth_provider != AuthProvider.LOCAL and self.identity_link_id is None:
            raise ValueError("External user sessions require an identity link.")
        if not _is_timezone_aware(self.created_at):
            raise ValueError("User session created_at must be timezone-aware.")
        if not _is_timezone_aware(self.last_seen_at):
            raise ValueError("User session last_seen_at must be timezone-aware.")
        if not _is_timezone_aware(self.expires_at):
            raise ValueError("User session expires_at must be timezone-aware.")
        if self.last_seen_at < self.created_at:
            raise ValueError("User session last_seen_at cannot be earlier than created_at.")
        if self.expires_at <= self.created_at:
            raise ValueError("User session expires_at must be later than created_at.")
        if self.client_label is not None and not self.client_label.strip():
            raise ValueError("User session client_label cannot be empty.")
        if self.revoked_at is not None:
            if not _is_timezone_aware(self.revoked_at):
                raise ValueError("User session revoked_at must be timezone-aware.")
            if self.revoked_at < self.created_at:
                raise ValueError("User session revoked_at cannot be earlier than created_at.")
            if self.revoked_reason is None:
                raise ValueError("User session revoked_reason is required when revoked.")
        if self.revoked_at is None and self.revoked_reason is not None:
            raise ValueError("User session revoked_reason requires revoked_at.")

    @property
    def is_revoked(self) -> bool:
        """Return whether the session has been explicitly revoked."""

        return self.revoked_at is not None

    def status_at(self, timestamp: datetime) -> UserSessionStatus:
        """Return the session lifecycle status at a timestamp."""

        if self.is_revoked:
            return UserSessionStatus.REVOKED
        if self.is_active_at(timestamp):
            return UserSessionStatus.ACTIVE

        return UserSessionStatus.EXPIRED

    def is_active_at(self, timestamp: datetime) -> bool:
        """Return whether the session can authenticate a request at a timestamp."""

        if not _is_timezone_aware(timestamp):
            raise ValueError("User session check timestamp must be timezone-aware.")

        return self.created_at <= timestamp < self.expires_at and not self.is_revoked

    def mark_seen(self, *, last_seen_at: datetime) -> UserSession:
        """Return a copy of the session with an updated last-seen timestamp."""

        return replace(self, last_seen_at=last_seen_at)

    def revoke(
        self,
        *,
        revoked_at: datetime,
        reason: SessionRevocationReason,
    ) -> UserSession:
        """Return a copy of the session marked as revoked."""

        return replace(self, revoked_at=revoked_at, revoked_reason=reason)


@dataclass(frozen=True, slots=True)
class SessionRefreshToken:
    """Rotating refresh token record for a DocMind browser session family."""

    id: UUID
    family_id: UUID
    session_id: UUID
    token_hash: RefreshTokenHash = field(repr=False)
    created_at: datetime
    expires_at: datetime
    rotated_at: datetime | None = None
    revoked_at: datetime | None = None
    reused_at: datetime | None = None

    def __post_init__(self) -> None:
        if not _is_timezone_aware(self.created_at):
            raise ValueError("Session refresh token created_at must be timezone-aware.")
        if not _is_timezone_aware(self.expires_at):
            raise ValueError("Session refresh token expires_at must be timezone-aware.")
        if self.expires_at <= self.created_at:
            raise ValueError(
                "Session refresh token expires_at must be later than created_at.",
            )
        for field_name, timestamp in (
            ("rotated_at", self.rotated_at),
            ("revoked_at", self.revoked_at),
            ("reused_at", self.reused_at),
        ):
            if timestamp is None:
                continue
            if not _is_timezone_aware(timestamp):
                raise ValueError(
                    f"Session refresh token {field_name} must be timezone-aware.",
                )
            if timestamp < self.created_at:
                raise ValueError(
                    f"Session refresh token {field_name} cannot be earlier than created_at.",
                )

    @property
    def is_rotated(self) -> bool:
        """Return whether this refresh token was replaced by a later token."""

        return self.rotated_at is not None

    @property
    def is_revoked(self) -> bool:
        """Return whether this refresh token family was explicitly revoked."""

        return self.revoked_at is not None

    @property
    def is_reused(self) -> bool:
        """Return whether reuse was detected for this token."""

        return self.reused_at is not None

    def is_active_at(self, timestamp: datetime) -> bool:
        """Return whether this refresh token can be used at a timestamp."""

        if not _is_timezone_aware(timestamp):
            raise ValueError("Session refresh token check timestamp must be timezone-aware.")

        return (
            self.created_at <= timestamp < self.expires_at
            and not self.is_rotated
            and not self.is_revoked
            and not self.is_reused
        )

    def rotate(self, *, rotated_at: datetime) -> SessionRefreshToken:
        """Return a copy marked as rotated."""

        return replace(self, rotated_at=rotated_at)

    def revoke(self, *, revoked_at: datetime) -> SessionRefreshToken:
        """Return a copy marked as revoked."""

        return replace(self, revoked_at=revoked_at)

    def mark_reused(self, *, reused_at: datetime) -> SessionRefreshToken:
        """Return a copy marked as reused."""

        return replace(self, reused_at=reused_at)


def _is_timezone_aware(value: datetime) -> bool:
    return value.tzinfo is not None and value.utcoffset() is not None
