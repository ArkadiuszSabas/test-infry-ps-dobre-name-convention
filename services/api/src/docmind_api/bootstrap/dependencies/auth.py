"""Auth dependency factories for the API service."""

from collections.abc import AsyncIterator, Mapping
from datetime import timedelta
from typing import Annotated

import httpx
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from docmind_api.application.auth.entra_claims import (
    EntraClaimsActorMapper,
    EntraClaimsMappingConfig,
)
from docmind_api.application.auth.entra_oidc import (
    CompleteEntraOidcLoginUseCase,
    EntraOidcLoginConfig,
    StartEntraOidcLoginUseCase,
)
from docmind_api.application.auth.entra_onboarding import EntraIdentityOnboardingUseCase
from docmind_api.application.auth.invitations import UserInvitationService
from docmind_api.application.auth.local_accounts import (
    LocalLoginHardeningConfig,
    LocalLoginUseCase,
    LocalUserService,
)
from docmind_api.application.auth.ports import ActorResolver
from docmind_api.application.auth.session_management import UserSessionManagementService
from docmind_api.application.auth.sessions import IssueBrowserSessionUseCase, UserSessionService
from docmind_api.bootstrap.dependencies.database import (
    get_database_session,
    get_database_session_factory,
)
from docmind_api.domain.auth.actors import Role
from docmind_api.infrastructure.auth.actor_resolver import (
    SessionActorResolver,
)
from docmind_api.infrastructure.auth.csrf_tokens import HmacCsrfTokenCodec
from docmind_api.infrastructure.auth.entra.config import (
    EntraIdTokenValidationConfig,
    EntraOidcTokenExchangeConfig,
)
from docmind_api.infrastructure.auth.entra.token_exchange import EntraOidcTokenExchanger
from docmind_api.infrastructure.auth.entra.token_validator import EntraIdTokenValidator
from docmind_api.infrastructure.auth.invitation_tokens import (
    SecretsInvitationTokenGenerator,
    Sha256InvitationTokenHasher,
)
from docmind_api.infrastructure.auth.local.password_hashing import Argon2idPasswordHasher
from docmind_api.infrastructure.auth.oidc import SecretsOidcAuthTransactionSecretGenerator
from docmind_api.infrastructure.auth.runtime import UtcClock, UuidIdGenerator
from docmind_api.infrastructure.auth.session_tokens import (
    SecretsRefreshTokenGenerator,
    SecretsSessionTokenGenerator,
    Sha256RefreshTokenHasher,
    Sha256SessionTokenHasher,
)
from docmind_api.infrastructure.persistence.auth.repositories import (
    SqlAlchemyDocMindUserRepository,
    SqlAlchemyIdentityLinkRepository,
    SqlAlchemyLocalLoginAttemptRecorder,
    SqlAlchemyLocalLoginAttemptRepository,
    SqlAlchemyLocalUserRepository,
    SqlAlchemyOidcAuthTransactionRepository,
    SqlAlchemyOidcAuthTransactionStateConsumer,
    SqlAlchemyRoleAssignmentRepository,
    SqlAlchemySessionActorRepository,
    SqlAlchemyUserInvitationRepository,
    SqlAlchemyUserSessionRepository,
)
from docmind_api.infrastructure.persistence.auth.session_refresh_tokens import (
    SqlAlchemyRefreshTokenFamilyRevoker,
    SqlAlchemySessionBoundRefreshTokenFamilyRevoker,
    SqlAlchemySessionRefreshTokenRepository,
)
from docmind_api.settings import (
    load_entra_id_provider_settings,
    load_local_auth_hardening_settings,
)

_SESSION_LIFETIME = timedelta(hours=8)
_REFRESH_TOKEN_LIFETIME = timedelta(days=30)
_OIDC_AUTH_TRANSACTION_TTL = timedelta(minutes=10)
_INVITATION_LIFETIME = timedelta(days=7)


async def get_entra_http_client() -> AsyncIterator[httpx.AsyncClient]:
    """Return a short-lived HTTP client for Entra provider calls."""

    async with httpx.AsyncClient() as http_client:
        yield http_client


def get_local_user_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> LocalUserService:
    """Return the local user application service."""

    return LocalUserService(
        repository=SqlAlchemyLocalUserRepository(session),
        password_hasher=Argon2idPasswordHasher(),
        clock=UtcClock(),
        id_generator=UuidIdGenerator(),
    )


def get_issue_browser_session_use_case(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> IssueBrowserSessionUseCase:
    """Return the shared browser session issuance use case."""

    return IssueBrowserSessionUseCase(
        repository=SqlAlchemyUserSessionRepository(session),
        actor_repository=SqlAlchemySessionActorRepository(session),
        token_generator=SecretsSessionTokenGenerator(),
        token_hasher=Sha256SessionTokenHasher(),
        refresh_repository=SqlAlchemySessionRefreshTokenRepository(session),
        refresh_token_generator=SecretsRefreshTokenGenerator(),
        refresh_token_hasher=Sha256RefreshTokenHasher(),
        csrf_token_codec=HmacCsrfTokenCodec(),
        clock=UtcClock(),
        id_generator=UuidIdGenerator(),
        refresh_token_id_generator=UuidIdGenerator(),
        refresh_token_family_id_generator=UuidIdGenerator(),
        session_lifetime=_SESSION_LIFETIME,
        refresh_token_lifetime=_REFRESH_TOKEN_LIFETIME,
    )


def get_local_login_use_case(
    local_user_service: Annotated[LocalUserService, Depends(get_local_user_service)],
    session_issuer: Annotated[
        IssueBrowserSessionUseCase,
        Depends(get_issue_browser_session_use_case),
    ],
    session: Annotated[AsyncSession, Depends(get_database_session)],
    session_factory: Annotated[
        async_sessionmaker[AsyncSession],
        Depends(get_database_session_factory),
    ],
) -> LocalLoginUseCase:
    """Return the local login use case."""

    hardening_settings = load_local_auth_hardening_settings()
    return LocalLoginUseCase(
        local_user_service=local_user_service,
        session_issuer=session_issuer,
        login_attempts=SqlAlchemyLocalLoginAttemptRepository(session),
        failed_login_attempts=SqlAlchemyLocalLoginAttemptRecorder(session_factory),
        clock=UtcClock(),
        hardening=LocalLoginHardeningConfig(
            max_failed_attempts=hardening_settings.max_failed_attempts,
            cooldown=timedelta(seconds=hardening_settings.cooldown_seconds),
        ),
    )


def get_start_entra_oidc_login_use_case(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> StartEntraOidcLoginUseCase:
    """Return the Entra OIDC login start use case."""

    return StartEntraOidcLoginUseCase(
        config=create_entra_oidc_login_config(),
        transactions=SqlAlchemyOidcAuthTransactionRepository(session),
        secret_generator=SecretsOidcAuthTransactionSecretGenerator(),
        clock=UtcClock(),
    )


def get_entra_identity_onboarding_use_case(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> EntraIdentityOnboardingUseCase:
    """Return the Entra identity onboarding use case."""

    return EntraIdentityOnboardingUseCase(
        users=SqlAlchemyDocMindUserRepository(session),
        identity_links=SqlAlchemyIdentityLinkRepository(session),
        role_assignments=SqlAlchemyRoleAssignmentRepository(session),
        clock=UtcClock(),
        user_id_generator=UuidIdGenerator(),
        identity_link_id_generator=UuidIdGenerator(),
    )


def get_entra_oidc_transaction_state_consumer(
    session_factory: Annotated[
        async_sessionmaker[AsyncSession],
        Depends(get_database_session_factory),
    ],
) -> SqlAlchemyOidcAuthTransactionStateConsumer:
    """Return a durable OIDC state consumer outside the request transaction."""

    return SqlAlchemyOidcAuthTransactionStateConsumer(session_factory)


def get_complete_entra_oidc_login_use_case(
    session: Annotated[AsyncSession, Depends(get_database_session)],
    transaction_state_consumer: Annotated[
        SqlAlchemyOidcAuthTransactionStateConsumer,
        Depends(get_entra_oidc_transaction_state_consumer),
    ],
    session_issuer: Annotated[
        IssueBrowserSessionUseCase,
        Depends(get_issue_browser_session_use_case),
    ],
    identity_onboarding: Annotated[
        EntraIdentityOnboardingUseCase,
        Depends(get_entra_identity_onboarding_use_case),
    ],
    http_client: Annotated[httpx.AsyncClient, Depends(get_entra_http_client)],
) -> CompleteEntraOidcLoginUseCase:
    """Return the Entra OIDC callback completion use case."""

    return CompleteEntraOidcLoginUseCase(
        config=create_entra_oidc_login_config(),
        transactions=SqlAlchemyOidcAuthTransactionRepository(session),
        transaction_state_consumer=transaction_state_consumer,
        secret_generator=SecretsOidcAuthTransactionSecretGenerator(),
        token_exchanger=EntraOidcTokenExchanger(
            config=create_entra_oidc_token_exchange_config(),
            http_client=http_client,
        ),
        id_token_validator=EntraIdTokenValidator(
            settings=create_entra_id_token_validation_config(),
            http_client=http_client,
        ),
        claims_mapper=EntraClaimsActorMapper(config=create_entra_claims_mapping_config()),
        identity_onboarding=identity_onboarding,
        session_issuer=session_issuer,
        clock=UtcClock(),
    )


def get_user_session_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
    session_factory: Annotated[
        async_sessionmaker[AsyncSession],
        Depends(get_database_session_factory),
    ],
    session_issuer: Annotated[
        IssueBrowserSessionUseCase,
        Depends(get_issue_browser_session_use_case),
    ],
) -> UserSessionService:
    """Return the browser session application service."""

    return UserSessionService(
        repository=SqlAlchemyUserSessionRepository(session),
        actor_repository=SqlAlchemySessionActorRepository(session),
        token_hasher=Sha256SessionTokenHasher(),
        refresh_repository=SqlAlchemySessionRefreshTokenRepository(session),
        refresh_family_revoker=SqlAlchemyRefreshTokenFamilyRevoker(session_factory),
        refresh_token_hasher=Sha256RefreshTokenHasher(),
        session_issuer=session_issuer,
        csrf_token_codec=HmacCsrfTokenCodec(),
        clock=UtcClock(),
    )


def get_user_session_management_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> UserSessionManagementService:
    """Return the browser session management application service."""

    return UserSessionManagementService(
        repository=SqlAlchemyUserSessionRepository(session),
        refresh_family_revoker=SqlAlchemySessionBoundRefreshTokenFamilyRevoker(session),
        clock=UtcClock(),
    )


def get_user_invitation_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> UserInvitationService:
    """Return the user invitation application service."""

    return UserInvitationService(
        repository=SqlAlchemyUserInvitationRepository(session),
        token_generator=SecretsInvitationTokenGenerator(),
        token_hasher=Sha256InvitationTokenHasher(),
        clock=UtcClock(),
        id_generator=UuidIdGenerator(),
        invitation_lifetime=_INVITATION_LIFETIME,
        delivery_available=False,
    )


def get_actor_resolver(
    session_service: Annotated[UserSessionService, Depends(get_user_session_service)],
) -> ActorResolver:
    """Return the configured actor resolver."""

    return SessionActorResolver(session_service)


def validate_auth_provider_configuration() -> None:
    """Validate auth provider settings that must fail fast at app configuration."""

    create_entra_claims_mapping_config()
    load_local_auth_hardening_settings()


def create_entra_claims_mapping_config() -> EntraClaimsMappingConfig:
    """Create Entra claim mapping config for login/session issuance."""

    settings = load_entra_id_provider_settings()
    return EntraClaimsMappingConfig(
        app_roles=_role_mapping(settings.app_role_mappings),
        groups=_role_mapping(settings.group_mappings),
    )


def create_entra_oidc_login_config() -> EntraOidcLoginConfig:
    """Create Entra OIDC login start config."""

    settings = load_entra_id_provider_settings()
    if (
        settings.client_id is None
        or settings.authorization_endpoint is None
        or settings.redirect_uri is None
    ):
        raise ValueError("Enabled Entra OIDC login requires start settings.")

    return EntraOidcLoginConfig(
        client_id=settings.client_id,
        authorization_endpoint=settings.authorization_endpoint,
        redirect_uri=settings.redirect_uri,
        post_login_redirect_targets=settings.post_login_redirect_targets,
        transaction_ttl=_OIDC_AUTH_TRANSACTION_TTL,
    )


def create_entra_oidc_token_exchange_config() -> EntraOidcTokenExchangeConfig:
    """Create Entra OIDC authorization code exchange config."""

    settings = load_entra_id_provider_settings()
    if (
        settings.token_endpoint is None
        or settings.client_id is None
        or settings.client_secret is None
    ):
        raise ValueError("Enabled Entra OIDC token exchange requires callback settings.")

    return EntraOidcTokenExchangeConfig(
        token_endpoint=settings.token_endpoint,
        client_id=settings.client_id,
        client_secret=settings.client_secret,
    )


def create_entra_id_token_validation_config() -> EntraIdTokenValidationConfig:
    """Create Entra ID token validation config for OIDC callbacks."""

    settings = load_entra_id_provider_settings()
    if settings.client_id is None:
        raise ValueError("Enabled Entra OIDC ID token validation requires client_id.")

    return EntraIdTokenValidationConfig(
        enabled=settings.enabled,
        tenant_id=settings.tenant_id,
        issuer=settings.issuer,
        audience=settings.client_id,
        discovery_url=settings.discovery_url,
        jwks_url=settings.jwks_url,
    )


def _role_mapping(mapping: Mapping[str, str]) -> Mapping[str, Role]:
    return {source: Role(role_value) for source, role_value in mapping.items()}
