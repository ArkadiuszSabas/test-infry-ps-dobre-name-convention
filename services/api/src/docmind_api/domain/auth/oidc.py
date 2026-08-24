"""Framework-free OIDC login transaction models."""

from dataclasses import dataclass, field, replace
from datetime import datetime


@dataclass(frozen=True, slots=True)
class OidcAuthTransaction:
    """Server-side state for an Authorization Code + PKCE login transaction."""

    state_hash: str
    nonce_hash: str
    browser_binding_hash: str
    pkce_verifier: str = field(repr=False)
    redirect_uri: str
    redirect_target: str
    created_at: datetime
    expires_at: datetime
    used_at: datetime | None = None

    def __post_init__(self) -> None:
        _require_non_empty(self.state_hash, "OIDC transaction state_hash")
        _require_non_empty(self.nonce_hash, "OIDC transaction nonce_hash")
        _require_non_empty(
            self.browser_binding_hash,
            "OIDC transaction browser_binding_hash",
        )
        _require_non_empty(self.pkce_verifier, "OIDC transaction PKCE verifier")
        _require_non_empty(self.redirect_uri, "OIDC transaction redirect_uri")
        _require_non_empty(self.redirect_target, "OIDC transaction redirect_target")

        _require_timezone_aware(self.created_at, "OIDC transaction created_at")
        _require_timezone_aware(self.expires_at, "OIDC transaction expires_at")
        if self.used_at is not None:
            _require_timezone_aware(self.used_at, "OIDC transaction used_at")

        if self.expires_at <= self.created_at:
            raise ValueError("OIDC transaction expires_at must be later than created_at.")
        if self.used_at is not None and self.used_at < self.created_at:
            raise ValueError("OIDC transaction used_at cannot be earlier than created_at.")

    @property
    def is_used(self) -> bool:
        return self.used_at is not None

    def is_active_at(self, timestamp: datetime) -> bool:
        """Return whether the transaction can still be consumed at the timestamp."""

        _require_timezone_aware(timestamp, "OIDC transaction activity timestamp")
        return self.created_at <= timestamp < self.expires_at and not self.is_used

    def mark_used(self, *, used_at: datetime) -> OidcAuthTransaction:
        """Return a copy marked as consumed by a callback."""

        if self.is_used:
            raise ValueError("OIDC transaction is already used.")

        return replace(self, used_at=used_at)


def _require_non_empty(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} cannot be empty.")


def _require_timezone_aware(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware.")
