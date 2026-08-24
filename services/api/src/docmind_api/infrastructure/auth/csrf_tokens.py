"""CSRF token infrastructure adapters."""

from base64 import urlsafe_b64encode
from collections.abc import Callable
from hashlib import sha256
from hmac import compare_digest
from hmac import new as hmac_new
from secrets import token_urlsafe

from docmind_api.application.auth.ports import OpaqueCsrfToken
from docmind_api.domain.auth.sessions import SessionTokenHash

_CSRF_TOKEN_VERSION = "v1"


class HmacCsrfTokenCodec:
    """Issue and validate browser-readable CSRF tokens bound to a session hash."""

    def __init__(
        self,
        *,
        nonce_byte_length: int = 32,
        nonce_factory: Callable[[int], str] = token_urlsafe,
    ) -> None:
        if nonce_byte_length <= 0:
            raise ValueError("CSRF token nonce byte length must be positive.")

        self._nonce_byte_length = nonce_byte_length
        self._nonce_factory = nonce_factory

    def issue_token(self, *, session_token_hash: SessionTokenHash) -> OpaqueCsrfToken:
        """Return a signed CSRF token scoped to a persisted session token hash."""

        nonce = self._nonce_factory(self._nonce_byte_length)
        return OpaqueCsrfToken(
            _encode_token(session_token_hash=session_token_hash, nonce=nonce),
        )

    def verify_token(
        self,
        *,
        token: OpaqueCsrfToken,
        session_token_hash: SessionTokenHash,
    ) -> bool:
        """Return whether the token signature matches the session token hash."""

        parts = token.value.split(".")
        if len(parts) != 3:
            return False

        version, nonce, signature = parts
        if version != _CSRF_TOKEN_VERSION or not nonce.strip() or not signature.strip():
            return False

        expected_token = _encode_token(
            session_token_hash=session_token_hash,
            nonce=nonce,
        )
        return compare_digest(token.value, expected_token)


def _encode_token(*, session_token_hash: SessionTokenHash, nonce: str) -> str:
    message = f"{_CSRF_TOKEN_VERSION}.{nonce}"
    signature = _signature(
        key=session_token_hash.value,
        message=message,
    )
    return f"{message}.{signature}"


def _signature(*, key: str, message: str) -> str:
    digest = hmac_new(
        key.encode("utf-8"),
        message.encode("utf-8"),
        sha256,
    ).digest()
    return urlsafe_b64encode(digest).decode("ascii").rstrip("=")
