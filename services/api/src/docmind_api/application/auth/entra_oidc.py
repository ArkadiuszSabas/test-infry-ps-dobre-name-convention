"""Entra ID OIDC login start use cases."""

from dataclasses import dataclass, field
from datetime import timedelta
from enum import StrEnum
from http import HTTPStatus
from typing import Protocol
from urllib.parse import urlencode, urlsplit, urlunsplit

from docmind_api.application.auth.entra_claims import EntraClaimsActorMapper
from docmind_api.application.auth.entra_onboarding import (
    EntraIdentityOnboardingCommand,
    EntraIdentityOnboardingResult,
)
from docmind_api.application.auth.ports import (
    Clock,
    EntraOidcIdTokenValidator,
    EntraOidcTokenExchangeCommand,
    EntraOidcTokenExchanger,
    OidcAuthTransactionRepository,
    OidcAuthTransactionSecretGenerator,
    OidcAuthTransactionStateConsumer,
    OpaqueRefreshToken,
    OpaqueSessionToken,
)
from docmind_api.application.auth.sessions import (
    BrowserSessionIssuer,
    IssueBrowserSessionCommand,
)
from docmind_api.domain.auth.actors import AuthenticatedActor, AuthProvider
from docmind_api.domain.auth.oidc import OidcAuthTransaction
from docmind_api.domain.auth.sessions import SessionRefreshToken, UserSession
from docmind_backend_runtime.errors import ApplicationError


@dataclass(frozen=True, slots=True)
class EntraOidcLoginConfig:
    client_id: str
    authorization_endpoint: str
    redirect_uri: str
    post_login_redirect_targets: tuple[str, ...]
    scopes: tuple[str, ...] = ("openid", "profile", "email")
    transaction_ttl: timedelta = timedelta(minutes=10)

    def __post_init__(self) -> None:
        if not self.client_id.strip():
            raise ValueError("Entra OIDC client_id cannot be empty.")
        if not self.authorization_endpoint.strip():
            raise ValueError("Entra OIDC authorization_endpoint cannot be empty.")
        if not self.redirect_uri.strip():
            raise ValueError("Entra OIDC redirect_uri cannot be empty.")
        if not self.post_login_redirect_targets:
            raise ValueError("Entra OIDC redirect targets cannot be empty.")
        if not self.scopes:
            raise ValueError("Entra OIDC scopes cannot be empty.")
        if self.transaction_ttl <= timedelta(0):
            raise ValueError("Entra OIDC transaction TTL must be positive.")


@dataclass(frozen=True, slots=True)
class StartEntraOidcLoginCommand:
    redirect_target: str


@dataclass(frozen=True, slots=True)
class StartedEntraOidcLogin:
    authorization_url: str
    browser_binding: str = field(repr=False)
    transaction_ttl: timedelta


@dataclass(frozen=True, slots=True)
class CompleteEntraOidcLoginCommand:
    code: str = field(repr=False)
    state: str = field(repr=False)
    browser_binding: str = field(repr=False)

    def __post_init__(self) -> None:
        if not self.code.strip():
            raise ValueError("Entra OIDC callback code cannot be empty.")
        if not self.state.strip():
            raise ValueError("Entra OIDC callback state cannot be empty.")
        if not self.browser_binding.strip():
            raise ValueError("Entra OIDC callback browser binding cannot be empty.")


@dataclass(frozen=True, slots=True)
class CompletedEntraOidcLogin:
    actor: AuthenticatedActor
    session: UserSession
    refresh_token_record: SessionRefreshToken
    redirect_target: str
    token: OpaqueSessionToken = field(repr=False)
    refresh_token: OpaqueRefreshToken = field(repr=False)


class EntraOidcCallbackFailureReason(StrEnum):
    PROVIDER_ERROR = "provider_error"
    MISSING_PARAMETERS = "missing_parameters"
    UNKNOWN_STATE = "unknown_state"
    EXPIRED_STATE = "expired_state"
    REUSED_STATE = "reused_state"
    TOKEN_EXCHANGE_FAILED = "token_exchange_failed"
    INVALID_ID_TOKEN = "invalid_id_token"
    INVALID_BROWSER_BINDING = "invalid_browser_binding"
    INVALID_NONCE = "invalid_nonce"
    UNMAPPED_IDENTITY = "unmapped_identity"
    SESSION_ISSUANCE_FAILED = "session_issuance_failed"


class EntraOidcRedirectTargetNotAllowedError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            code="ENTRA_OIDC_REDIRECT_TARGET_NOT_ALLOWED",
            message="Entra OIDC redirect target is not allowed.",
            status_code=HTTPStatus.BAD_REQUEST,
        )


class EntraOidcCallbackRejectedError(ApplicationError):
    def __init__(self, *, reason: EntraOidcCallbackFailureReason) -> None:
        super().__init__(
            code="ENTRA_OIDC_CALLBACK_REJECTED",
            message="Entra OIDC callback was rejected.",
            status_code=HTTPStatus.UNAUTHORIZED,
            details={"reason": reason.value},
        )
        self.reason = reason


class EntraIdentityOnboarding(Protocol):
    async def execute(
        self,
        command: EntraIdentityOnboardingCommand,
    ) -> EntraIdentityOnboardingResult | None: ...


class StartEntraOidcLoginUseCase:
    def __init__(
        self,
        *,
        config: EntraOidcLoginConfig,
        transactions: OidcAuthTransactionRepository,
        secret_generator: OidcAuthTransactionSecretGenerator,
        clock: Clock,
    ) -> None:
        self._config = config
        self._transactions = transactions
        self._secret_generator = secret_generator
        self._clock = clock
        self._allowed_redirect_targets = frozenset(
            _normalize_url(target) for target in config.post_login_redirect_targets
        )

    async def execute(
        self,
        command: StartEntraOidcLoginCommand,
    ) -> StartedEntraOidcLogin:
        redirect_target = _normalize_url(command.redirect_target)
        if redirect_target not in self._allowed_redirect_targets:
            raise EntraOidcRedirectTargetNotAllowedError()

        timestamp = self._clock.now()
        state = self._secret_generator.new_state()
        nonce = self._secret_generator.new_nonce()
        browser_binding = self._secret_generator.new_browser_binding()
        pkce_verifier = self._secret_generator.new_pkce_verifier()
        code_challenge = self._secret_generator.pkce_challenge(pkce_verifier)

        await self._transactions.add(
            OidcAuthTransaction(
                state_hash=self._secret_generator.hash_secret(state),
                nonce_hash=self._secret_generator.hash_secret(nonce),
                browser_binding_hash=self._secret_generator.hash_secret(browser_binding),
                pkce_verifier=pkce_verifier,
                redirect_uri=self._config.redirect_uri,
                redirect_target=redirect_target,
                created_at=timestamp,
                expires_at=timestamp + self._config.transaction_ttl,
            ),
        )

        return StartedEntraOidcLogin(
            authorization_url=self._authorization_url(
                state=state,
                nonce=nonce,
                code_challenge=code_challenge,
            ),
            browser_binding=browser_binding,
            transaction_ttl=self._config.transaction_ttl,
        )

    def _authorization_url(
        self,
        *,
        state: str,
        nonce: str,
        code_challenge: str,
    ) -> str:
        query = urlencode(
            {
                "client_id": self._config.client_id,
                "response_type": "code",
                "redirect_uri": self._config.redirect_uri,
                "scope": " ".join(self._config.scopes),
                "state": state,
                "nonce": nonce,
                "code_challenge": code_challenge,
                "code_challenge_method": "S256",
            },
        )
        separator = "&" if "?" in self._config.authorization_endpoint else "?"
        return f"{self._config.authorization_endpoint}{separator}{query}"


class CompleteEntraOidcLoginUseCase:
    def __init__(
        self,
        *,
        config: EntraOidcLoginConfig,
        transactions: OidcAuthTransactionRepository,
        transaction_state_consumer: OidcAuthTransactionStateConsumer,
        secret_generator: OidcAuthTransactionSecretGenerator,
        token_exchanger: EntraOidcTokenExchanger,
        id_token_validator: EntraOidcIdTokenValidator,
        claims_mapper: EntraClaimsActorMapper,
        identity_onboarding: EntraIdentityOnboarding,
        session_issuer: BrowserSessionIssuer,
        clock: Clock,
    ) -> None:
        self._config = config
        self._transactions = transactions
        self._transaction_state_consumer = transaction_state_consumer
        self._secret_generator = secret_generator
        self._token_exchanger = token_exchanger
        self._id_token_validator = id_token_validator
        self._claims_mapper = claims_mapper
        self._identity_onboarding = identity_onboarding
        self._session_issuer = session_issuer
        self._clock = clock

    async def execute(
        self,
        command: CompleteEntraOidcLoginCommand,
    ) -> CompletedEntraOidcLogin:
        timestamp = self._clock.now()
        transaction = await self._transactions.get_by_state_hash(
            self._secret_generator.hash_secret(command.state),
        )
        if transaction is None:
            raise _callback_rejected(EntraOidcCallbackFailureReason.UNKNOWN_STATE)

        if not transaction.is_active_at(timestamp):
            reason = (
                EntraOidcCallbackFailureReason.REUSED_STATE
                if transaction.is_used
                else EntraOidcCallbackFailureReason.EXPIRED_STATE
            )
            raise _callback_rejected(reason)

        if (
            self._secret_generator.hash_secret(command.browser_binding)
            != transaction.browser_binding_hash
        ):
            raise _callback_rejected(EntraOidcCallbackFailureReason.INVALID_BROWSER_BINDING)

        state_marked_used = await self._transaction_state_consumer.mark_used(
            transaction.state_hash,
            timestamp,
        )
        if not state_marked_used:
            raise _callback_rejected(EntraOidcCallbackFailureReason.REUSED_STATE)

        token_response = await self._token_exchanger.exchange_code(
            EntraOidcTokenExchangeCommand(
                code=command.code,
                redirect_uri=self._config.redirect_uri,
                pkce_verifier=transaction.pkce_verifier,
            ),
        )
        if token_response is None:
            raise _callback_rejected(EntraOidcCallbackFailureReason.TOKEN_EXCHANGE_FAILED)

        validated_token = await self._id_token_validator.validate_id_token(
            token_response.id_token,
        )
        if validated_token is None:
            raise _callback_rejected(EntraOidcCallbackFailureReason.INVALID_ID_TOKEN)

        nonce_claim = validated_token.claims.get("nonce")
        if (
            not isinstance(nonce_claim, str)
            or self._secret_generator.hash_secret(nonce_claim) != transaction.nonce_hash
        ):
            raise _callback_rejected(EntraOidcCallbackFailureReason.INVALID_NONCE)

        identity = self._claims_mapper.map_identity(validated_token)
        if identity is None:
            raise _callback_rejected(EntraOidcCallbackFailureReason.UNMAPPED_IDENTITY)

        onboarding_result = await self._identity_onboarding.execute(
            EntraIdentityOnboardingCommand(identity=identity),
        )
        if onboarding_result is None:
            raise _callback_rejected(EntraOidcCallbackFailureReason.UNMAPPED_IDENTITY)

        issued_session = await self._session_issuer.execute(
            IssueBrowserSessionCommand(
                user_id=onboarding_result.user_id,
                auth_provider=AuthProvider.ENTRA_ID,
                identity_link_id=onboarding_result.identity_link_id,
            ),
        )
        if issued_session is None:
            raise _callback_rejected(EntraOidcCallbackFailureReason.SESSION_ISSUANCE_FAILED)

        return CompletedEntraOidcLogin(
            actor=issued_session.actor,
            session=issued_session.session,
            token=issued_session.token,
            refresh_token=issued_session.refresh_token,
            refresh_token_record=issued_session.refresh_token_record,
            redirect_target=transaction.redirect_target,
        )


def _normalize_url(value: str) -> str:
    stripped_value = value.strip()
    parsed_value = urlsplit(stripped_value)
    if not parsed_value.scheme or not parsed_value.netloc:
        return stripped_value

    return urlunsplit(
        (
            parsed_value.scheme.lower(),
            parsed_value.netloc.lower(),
            parsed_value.path.rstrip("/") or "/",
            parsed_value.query,
            "",
        ),
    )


def _callback_rejected(
    reason: EntraOidcCallbackFailureReason,
) -> EntraOidcCallbackRejectedError:
    return EntraOidcCallbackRejectedError(reason=reason)
