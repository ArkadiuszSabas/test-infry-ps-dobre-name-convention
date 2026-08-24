"""DocMind browser session token infrastructure adapters."""

from collections.abc import Callable
from hashlib import sha256
from secrets import token_urlsafe

from docmind_api.application.auth.ports import OpaqueRefreshToken, OpaqueSessionToken
from docmind_api.domain.auth.sessions import RefreshTokenHash, SessionTokenHash


class SecretsSessionTokenGenerator:
    """Generate opaque browser session tokens using OS-backed randomness."""

    def __init__(
        self,
        *,
        byte_length: int = 32,
        token_factory: Callable[[int], str] = token_urlsafe,
    ) -> None:
        if byte_length <= 0:
            raise ValueError("Session token byte length must be positive.")

        self._byte_length = byte_length
        self._token_factory = token_factory

    def new_token(self) -> OpaqueSessionToken:
        """Return a new opaque token for an HttpOnly session cookie."""

        return OpaqueSessionToken(self._token_factory(self._byte_length))


class Sha256SessionTokenHasher:
    """Hash opaque session tokens before they are persisted."""

    def hash_token(self, token: OpaqueSessionToken) -> SessionTokenHash:
        """Return the SHA-256 hex digest for a raw opaque token."""

        digest = sha256(token.value.encode("utf-8")).hexdigest()
        return SessionTokenHash(digest)


class SecretsRefreshTokenGenerator:
    """Generate opaque browser refresh tokens using OS-backed randomness."""

    def __init__(self, *, byte_length: int = 32) -> None:
        if byte_length <= 0:
            raise ValueError("Refresh token byte length must be positive.")

        self._byte_length = byte_length

    def new_token(self) -> OpaqueRefreshToken:
        """Return a new opaque token for an HttpOnly refresh cookie."""

        return OpaqueRefreshToken(token_urlsafe(self._byte_length))


class Sha256RefreshTokenHasher:
    """Hash opaque refresh tokens before they are persisted."""

    def hash_token(self, token: OpaqueRefreshToken) -> RefreshTokenHash:
        """Return the SHA-256 hex digest for a raw opaque refresh token."""

        digest = sha256(token.value.encode("utf-8")).hexdigest()
        return RefreshTokenHash(digest)
