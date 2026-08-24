"""OIDC auth transaction secret infrastructure adapters."""

from base64 import urlsafe_b64encode
from hashlib import sha256
from secrets import token_urlsafe


class SecretsOidcAuthTransactionSecretGenerator:
    """Generate OIDC state, nonce, and PKCE values with OS-backed randomness."""

    def __init__(
        self,
        *,
        state_byte_length: int = 32,
        nonce_byte_length: int = 32,
        browser_binding_byte_length: int = 32,
        pkce_verifier_byte_length: int = 32,
    ) -> None:
        if state_byte_length <= 0:
            raise ValueError("OIDC state byte length must be positive.")
        if nonce_byte_length <= 0:
            raise ValueError("OIDC nonce byte length must be positive.")
        if browser_binding_byte_length <= 0:
            raise ValueError("OIDC browser binding byte length must be positive.")
        if pkce_verifier_byte_length <= 0:
            raise ValueError("OIDC PKCE verifier byte length must be positive.")

        self._state_byte_length = state_byte_length
        self._nonce_byte_length = nonce_byte_length
        self._browser_binding_byte_length = browser_binding_byte_length
        self._pkce_verifier_byte_length = pkce_verifier_byte_length

    def new_state(self) -> str:
        """Return a new raw OIDC state value for the browser redirect."""

        return token_urlsafe(self._state_byte_length)

    def new_nonce(self) -> str:
        """Return a new raw OIDC nonce value for the provider authorization request."""

        return token_urlsafe(self._nonce_byte_length)

    def new_browser_binding(self) -> str:
        """Return a browser-bound OIDC transaction secret stored in an HttpOnly cookie."""

        return token_urlsafe(self._browser_binding_byte_length)

    def new_pkce_verifier(self) -> str:
        """Return a new PKCE code verifier stored only server-side."""

        return token_urlsafe(self._pkce_verifier_byte_length)

    def hash_secret(self, value: str) -> str:
        """Return a SHA-256 hex digest for a raw state or nonce secret."""

        _require_non_empty_secret(value)
        return sha256(value.encode("utf-8")).hexdigest()

    def pkce_challenge(self, verifier: str) -> str:
        """Return an RFC 7636 S256 PKCE challenge for a verifier."""

        _require_non_empty_secret(verifier)
        digest = sha256(verifier.encode("ascii")).digest()
        return urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def _require_non_empty_secret(value: str) -> None:
    if not value.strip():
        raise ValueError("OIDC secret cannot be empty.")
