"""Provider-neutral application auth ports used by API authorization dependencies."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol
from uuid import UUID

from docmind_api.application.auth.repository_ports import (
    DocMindUserRepository as DocMindUserRepository,
)
from docmind_api.application.auth.repository_ports import (
    FirstAdminBootstrapRepository as FirstAdminBootstrapRepository,
)
from docmind_api.application.auth.repository_ports import (
    IdentityLinkRepository as IdentityLinkRepository,
)
from docmind_api.application.auth.repository_ports import (
    LocalLoginAttemptRecorder as LocalLoginAttemptRecorder,
)
from docmind_api.application.auth.repository_ports import (
    LocalLoginAttemptRepository as LocalLoginAttemptRepository,
)
from docmind_api.application.auth.repository_ports import (
    LocalUserRepository as LocalUserRepository,
)
from docmind_api.application.auth.repository_ports import (
    ManagedUserRepository as ManagedUserRepository,
)
from docmind_api.application.auth.repository_ports import (
    OidcAuthTransactionRepository as OidcAuthTransactionRepository,
)
from docmind_api.application.auth.repository_ports import (
    OidcAuthTransactionStateConsumer as OidcAuthTransactionStateConsumer,
)
from docmind_api.application.auth.repository_ports import (
    RefreshTokenFamilyRevoker as RefreshTokenFamilyRevoker,
)
from docmind_api.application.auth.repository_ports import (
    RefreshTokenRepository as RefreshTokenRepository,
)
from docmind_api.application.auth.repository_ports import (
    RoleAssignmentRepository as RoleAssignmentRepository,
)
from docmind_api.application.auth.repository_ports import (
    SessionActorContext as SessionActorContext,
)
from docmind_api.application.auth.repository_ports import (
    SessionActorRepository as SessionActorRepository,
)
from docmind_api.application.auth.repository_ports import (
    UserInvitationRepository as UserInvitationRepository,
)
from docmind_api.application.auth.repository_ports import (
    UserSessionBulkRevoker as UserSessionBulkRevoker,
)
from docmind_api.application.auth.repository_ports import (
    UserSessionRepository as UserSessionRepository,
)
from docmind_api.domain.auth.actors import AuthenticatedActor
from docmind_api.domain.auth.invitations import InvitationTokenHash
from docmind_api.domain.auth.local_accounts import PasswordHash
from docmind_api.domain.auth.sessions import (
    RefreshTokenHash,
    SessionTokenHash,
)


@dataclass(frozen=True, slots=True)
class ActorCredentials:
    """Raw authentication inputs extracted from the HTTP request boundary."""

    authorization: str | None = None
    session_id: str | None = None


@dataclass(frozen=True, slots=True)
class OpaqueSessionToken:
    """Raw opaque session token issued to a browser cookie."""

    value: str = field(repr=False)

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise ValueError("Opaque session token cannot be empty.")


@dataclass(frozen=True, slots=True)
class OpaqueRefreshToken:
    """Raw opaque refresh token issued to a browser cookie."""

    value: str = field(repr=False)

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise ValueError("Opaque refresh token cannot be empty.")


@dataclass(frozen=True, slots=True)
class OpaqueCsrfToken:
    """Browser-readable CSRF token bound to a DocMind session."""

    value: str = field(repr=False)

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise ValueError("Opaque CSRF token cannot be empty.")


@dataclass(frozen=True, slots=True)
class OpaqueInvitationToken:
    """Raw one-time invitation token that must never be logged or returned by APIs."""

    value: str = field(repr=False)

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise ValueError("Opaque invitation token cannot be empty.")


class ActorResolver(Protocol):
    """Resolves request credentials into a provider-neutral authenticated actor."""

    async def resolve_actor(
        self,
        credentials: ActorCredentials,
    ) -> AuthenticatedActor | None:
        """Return an authenticated actor when credentials are valid."""


@dataclass(frozen=True, slots=True)
class ValidatedAccessToken:
    """Provider-neutral claims from a verified access token."""

    subject: str
    issuer: str
    audience: str | tuple[str, ...]
    tenant_id: str | None
    claims: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class EntraOidcTokenExchangeCommand:
    """Input for exchanging an Entra OIDC authorization code server-side."""

    code: str = field(repr=False)
    redirect_uri: str
    pkce_verifier: str = field(repr=False)

    def __post_init__(self) -> None:
        if not self.code.strip():
            raise ValueError("Entra OIDC authorization code cannot be empty.")
        if not self.redirect_uri.strip():
            raise ValueError("Entra OIDC redirect_uri cannot be empty.")
        if not self.pkce_verifier.strip():
            raise ValueError("Entra OIDC PKCE verifier cannot be empty.")


@dataclass(frozen=True, slots=True)
class EntraOidcTokenResponse:
    """Trusted shape returned by an Entra OIDC token exchange adapter."""

    id_token: str = field(repr=False)
    access_token: str | None = field(default=None, repr=False)
    token_type: str | None = None
    expires_in: int | None = None

    def __post_init__(self) -> None:
        if not self.id_token.strip():
            raise ValueError("Entra OIDC id_token cannot be empty.")
        if self.access_token is not None and not self.access_token.strip():
            raise ValueError("Entra OIDC access_token cannot be empty when provided.")
        if self.expires_in is not None and self.expires_in <= 0:
            raise ValueError("Entra OIDC expires_in must be positive when provided.")


class AccessTokenValidator(Protocol):
    """Validates raw bearer access tokens and returns trusted claims."""

    async def validate_access_token(self, token: str) -> ValidatedAccessToken | None:
        """Return trusted token claims when the token is valid."""


class EntraOidcTokenExchanger(Protocol):
    """Exchanges Entra authorization codes for provider tokens."""

    async def exchange_code(
        self,
        command: EntraOidcTokenExchangeCommand,
    ) -> EntraOidcTokenResponse | None: ...


class EntraOidcIdTokenValidator(Protocol):
    """Validates Entra OIDC ID tokens returned by the callback token exchange."""

    async def validate_id_token(self, token: str) -> ValidatedAccessToken | None: ...


class Clock(Protocol):
    """Port for obtaining audit timestamps."""

    def now(self) -> datetime: ...


class LocalUserIdGenerator(Protocol):
    """Port for generating local user identifiers."""

    def new_id(self) -> UUID: ...


class UserSessionIdGenerator(Protocol):
    """Port for generating browser session identifiers."""

    def new_id(self) -> UUID: ...


class RefreshTokenIdGenerator(Protocol):
    """Port for generating refresh token record identifiers."""

    def new_id(self) -> UUID: ...


class RefreshTokenFamilyIdGenerator(Protocol):
    """Port for generating refresh token family identifiers."""

    def new_id(self) -> UUID: ...


class OidcAuthTransactionSecretGenerator(Protocol):
    """Port for generating and deriving OIDC auth transaction secrets."""

    def new_state(self) -> str: ...

    def new_nonce(self) -> str: ...

    def new_browser_binding(self) -> str: ...

    def new_pkce_verifier(self) -> str: ...

    def hash_secret(self, value: str) -> str: ...

    def pkce_challenge(self, verifier: str) -> str: ...


class DocMindUserIdGenerator(Protocol):
    """Port for generating DocMind user identifiers."""

    def new_id(self) -> UUID: ...


class IdentityLinkIdGenerator(Protocol):
    """Port for generating external identity link identifiers."""

    def new_id(self) -> UUID: ...


class PasswordHasher(Protocol):
    """Port implemented by password hashing adapters."""

    async def hash_password(self, plaintext_password: str) -> PasswordHash: ...

    async def verify_password(
        self, plaintext_password: str, password_hash: PasswordHash
    ) -> bool: ...

    def verification_fallback_hash(self) -> PasswordHash: ...


class SessionTokenGenerator(Protocol):
    """Port implemented by opaque browser session token generators."""

    def new_token(self) -> OpaqueSessionToken: ...


class SessionTokenHasher(Protocol):
    """Port implemented by opaque browser session token hashers."""

    def hash_token(self, token: OpaqueSessionToken) -> SessionTokenHash: ...


class RefreshTokenGenerator(Protocol):
    """Port implemented by opaque browser refresh token generators."""

    def new_token(self) -> OpaqueRefreshToken: ...


class RefreshTokenHasher(Protocol):
    """Port implemented by opaque browser refresh token hashers."""

    def hash_token(self, token: OpaqueRefreshToken) -> RefreshTokenHash: ...


class CsrfTokenCodec(Protocol):
    """Port implemented by CSRF token issuers and validators."""

    def issue_token(self, *, session_token_hash: SessionTokenHash) -> OpaqueCsrfToken:
        """Return a CSRF token bound to the persisted session token hash."""
        ...

    def verify_token(
        self,
        *,
        token: OpaqueCsrfToken,
        session_token_hash: SessionTokenHash,
    ) -> bool:
        """Return whether a CSRF token belongs to the session token hash."""
        ...


class InvitationTokenGenerator(Protocol):
    """Port for issuing one-time invitation token material."""

    def new_token(self) -> OpaqueInvitationToken: ...


class InvitationTokenHasher(Protocol):
    """Port for hashing one-time invitation token material."""

    def hash_token(self, token: OpaqueInvitationToken) -> InvitationTokenHash: ...
