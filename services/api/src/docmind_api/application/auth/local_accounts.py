"""Local account application use cases."""

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from http import HTTPStatus

from docmind_api.application.auth.ports import (
    Clock,
    LocalLoginAttemptRecorder,
    LocalLoginAttemptRepository,
    LocalUserIdGenerator,
    LocalUserRepository,
    OpaqueCsrfToken,
    OpaqueRefreshToken,
    OpaqueSessionToken,
    PasswordHasher,
)
from docmind_api.application.auth.sessions import (
    BrowserSessionIssuer,
    IssueBrowserSessionCommand,
)
from docmind_api.domain.auth.actors import AuthenticatedActor, AuthProvider
from docmind_api.domain.auth.local_accounts import (
    LocalLoginAttempt,
    LocalUser,
    LocalUserStatus,
    normalize_login,
    normalize_roles,
)
from docmind_api.domain.auth.sessions import (
    SessionClientMetadata,
    SessionRefreshToken,
    UserSession,
)
from docmind_backend_runtime.errors import (
    ApplicationError,
    ConflictError,
    ValidationApplicationError,
)


@dataclass(frozen=True, slots=True)
class CreateLocalUserCommand:
    """Input for creating a local user account."""

    login: str
    display_name: str
    plaintext_password: str = field(repr=False)
    roles: tuple[str, ...]
    status: LocalUserStatus = LocalUserStatus.ACTIVE


@dataclass(frozen=True, slots=True)
class AuthenticateLocalUserCommand:
    """Input for verifying local user credentials."""

    login: str
    plaintext_password: str = field(repr=False)


@dataclass(frozen=True, slots=True)
class LocalLoginCommand:
    """Input for completing local login and issuing a browser session."""

    login: str
    plaintext_password: str = field(repr=False)
    client_metadata: SessionClientMetadata = field(default_factory=SessionClientMetadata)


@dataclass(frozen=True, slots=True)
class LocalLoginResult:
    """Result of local login after issuing a DocMind browser session."""

    actor: AuthenticatedActor
    session: UserSession
    refresh_token_record: SessionRefreshToken
    token: OpaqueSessionToken = field(repr=False)
    refresh_token: OpaqueRefreshToken = field(repr=False)
    csrf_token: OpaqueCsrfToken = field(repr=False)


@dataclass(frozen=True, slots=True)
class LocalLoginHardeningConfig:
    """MVP hardening policy for local username/password login."""

    max_failed_attempts: int
    cooldown: timedelta

    def __post_init__(self) -> None:
        if self.max_failed_attempts < 1:
            raise ValueError("Local login max failed attempts must be positive.")
        if self.cooldown <= timedelta(0):
            raise ValueError("Local login cooldown must be positive.")


class LocalAuthenticationFailureReason(StrEnum):
    """Internal reason why local authentication failed."""

    INVALID_CREDENTIALS = "invalid_credentials"
    INACTIVE_USER = "inactive_user"
    DELETED_USER = "deleted_user"


@dataclass(frozen=True, slots=True)
class LocalAuthenticationResult:
    """Result of a local authentication attempt."""

    authenticated: bool
    user: LocalUser | None
    failure_reason: LocalAuthenticationFailureReason | None

    @classmethod
    def success(cls, user: LocalUser) -> LocalAuthenticationResult:
        """Return a successful local authentication result."""

        return cls(authenticated=True, user=user, failure_reason=None)

    @classmethod
    def failure(
        cls,
        reason: LocalAuthenticationFailureReason,
    ) -> LocalAuthenticationResult:
        """Return a failed local authentication result."""

        return cls(authenticated=False, user=None, failure_reason=reason)


class LocalUserAlreadyExistsError(ConflictError):
    """Raised when a local login is already registered."""

    def __init__(self, *, login: str) -> None:
        super().__init__(
            code="LOCAL_USER_ALREADY_EXISTS",
            message="Local user already exists.",
            details={"login": login},
        )
        self.login = login


class LocalUserValidationError(ValidationApplicationError):
    """Raised when local user command input is invalid."""

    def __init__(self, *, message: str) -> None:
        super().__init__(
            code="LOCAL_USER_VALIDATION_ERROR",
            message=message,
        )


class InvalidLocalCredentialsError(ApplicationError):
    """Raised when local login credentials are invalid."""

    def __init__(self) -> None:
        super().__init__(
            code="INVALID_CREDENTIALS",
            message="Invalid login or password.",
            status_code=HTTPStatus.UNAUTHORIZED,
        )


class LocalLoginTemporarilyLockedError(ApplicationError):
    """Raised when local login is under failed-attempt cooldown."""

    def __init__(self, *, retry_after_seconds: int, locked_until: datetime) -> None:
        super().__init__(
            code="LOCAL_LOGIN_TEMPORARILY_LOCKED",
            message="Local login is temporarily locked.",
            status_code=HTTPStatus.TOO_MANY_REQUESTS,
            details={
                "retry_after_seconds": retry_after_seconds,
                "locked_until": _utc_isoformat(locked_until),
            },
        )


class LocalAccountDisabledError(ApplicationError):
    """Raised when local credentials are valid but the account cannot authenticate."""

    def __init__(self) -> None:
        super().__init__(
            code="LOCAL_ACCOUNT_DISABLED",
            message="Local account is disabled.",
            status_code=HTTPStatus.FORBIDDEN,
        )


class LocalUserService:
    """Application service for local user lifecycle and credential checks."""

    def __init__(
        self,
        *,
        repository: LocalUserRepository,
        password_hasher: PasswordHasher,
        clock: Clock,
        id_generator: LocalUserIdGenerator,
    ) -> None:
        self._repository = repository
        self._password_hasher = password_hasher
        self._clock = clock
        self._id_generator = id_generator

    async def create_user(self, command: CreateLocalUserCommand) -> LocalUser:
        """Create a local user with a hashed password."""

        try:
            login = normalize_login(command.login)
            roles = normalize_roles(command.roles)
        except ValueError as error:
            raise LocalUserValidationError(message=str(error)) from error
        if not command.plaintext_password.strip():
            raise LocalUserValidationError(message="Local user password cannot be empty.")

        existing_user = await self._repository.get_by_login(login)
        if existing_user is not None:
            raise LocalUserAlreadyExistsError(login=login)

        timestamp = self._clock.now()
        try:
            user = LocalUser(
                id=self._id_generator.new_id(),
                login=login,
                display_name=command.display_name.strip(),
                status=command.status,
                roles=roles,
                password_hash=await self._password_hasher.hash_password(command.plaintext_password),
                created_at=timestamp,
                updated_at=timestamp,
            )
        except ValueError as error:
            raise LocalUserValidationError(message=str(error)) from error

        await self._repository.add(user)
        return user

    async def authenticate(
        self,
        command: AuthenticateLocalUserCommand,
    ) -> LocalAuthenticationResult:
        """Verify local credentials and account status."""

        try:
            login = normalize_login(command.login)
        except ValueError:
            await self._verify_against_fallback_hash(command.plaintext_password)
            return LocalAuthenticationResult.failure(
                LocalAuthenticationFailureReason.INVALID_CREDENTIALS,
            )

        user = await self._repository.get_by_login(login)
        password_hash = (
            user.password_hash
            if user is not None
            else self._password_hasher.verification_fallback_hash()
        )

        password_matches = await self._password_hasher.verify_password(
            command.plaintext_password,
            password_hash,
        )
        if user is None or not password_matches:
            return LocalAuthenticationResult.failure(
                LocalAuthenticationFailureReason.INVALID_CREDENTIALS,
            )

        if user.status == LocalUserStatus.DELETED:
            return LocalAuthenticationResult.failure(
                LocalAuthenticationFailureReason.DELETED_USER,
            )

        if user.status == LocalUserStatus.INACTIVE:
            return LocalAuthenticationResult.failure(
                LocalAuthenticationFailureReason.INACTIVE_USER,
            )

        return LocalAuthenticationResult.success(user)

    async def _verify_against_fallback_hash(self, plaintext_password: str) -> bool:
        return await self._password_hasher.verify_password(
            plaintext_password,
            self._password_hasher.verification_fallback_hash(),
        )


class LocalLoginUseCase:
    """Application use case for local credentials login and session issuance."""

    def __init__(
        self,
        *,
        local_user_service: LocalUserService,
        session_issuer: BrowserSessionIssuer,
        login_attempts: LocalLoginAttemptRepository,
        failed_login_attempts: LocalLoginAttemptRecorder,
        clock: Clock,
        hardening: LocalLoginHardeningConfig,
    ) -> None:
        self._local_user_service = local_user_service
        self._session_issuer = session_issuer
        self._login_attempts = login_attempts
        self._failed_login_attempts = failed_login_attempts
        self._clock = clock
        self._hardening = hardening

    async def execute(self, command: LocalLoginCommand) -> LocalLoginResult:
        """Verify local credentials, issue a session, and return current actor state."""

        timestamp = self._clock.now()
        login = _normalized_login_or_none(command.login)
        attempt = await self._get_current_attempt(login)
        if attempt is not None and attempt.is_locked_at(timestamp):
            locked_until = attempt.locked_until
            if locked_until is None:
                raise InvalidLocalCredentialsError()
            raise LocalLoginTemporarilyLockedError(
                retry_after_seconds=_retry_after_seconds(
                    locked_until=locked_until,
                    timestamp=timestamp,
                ),
                locked_until=locked_until,
            )

        auth_result = await self._local_user_service.authenticate(
            AuthenticateLocalUserCommand(
                login=command.login,
                plaintext_password=command.plaintext_password,
            ),
        )
        if auth_result.failure_reason == LocalAuthenticationFailureReason.INACTIVE_USER:
            raise LocalAccountDisabledError()

        if not auth_result.authenticated or auth_result.user is None:
            await self._record_failed_attempt(
                login=login,
                failed_at=timestamp,
            )
            raise InvalidLocalCredentialsError()

        if login is not None:
            await self._login_attempts.reset(login)

        issued_session = await self._session_issuer.execute(
            IssueBrowserSessionCommand(
                user_id=auth_result.user.id,
                auth_provider=AuthProvider.LOCAL,
                identity_link_id=None,
                client_metadata=command.client_metadata,
            ),
        )
        if issued_session is None:
            raise InvalidLocalCredentialsError()

        return LocalLoginResult(
            actor=issued_session.actor,
            session=issued_session.session,
            token=issued_session.token,
            refresh_token=issued_session.refresh_token,
            refresh_token_record=issued_session.refresh_token_record,
            csrf_token=issued_session.csrf_token,
        )

    async def _get_current_attempt(self, login: str | None) -> LocalLoginAttempt | None:
        if login is None:
            return None

        return await self._login_attempts.get_by_login(login)

    async def _record_failed_attempt(
        self,
        *,
        login: str | None,
        failed_at: datetime,
    ) -> None:
        if login is None:
            return

        await self._failed_login_attempts.record_failed_attempt(
            login=login,
            failed_at=failed_at,
            max_failed_attempts=self._hardening.max_failed_attempts,
            cooldown=self._hardening.cooldown,
        )


def _normalized_login_or_none(login: str) -> str | None:
    try:
        return normalize_login(login)
    except ValueError:
        return None


def _retry_after_seconds(*, locked_until: datetime | None, timestamp: datetime) -> int:
    if locked_until is None:
        return 1

    retry_after = locked_until - timestamp
    return max(1, int(retry_after.total_seconds()))


def _utc_isoformat(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
