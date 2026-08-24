"""Self-service local password use cases."""

from dataclasses import dataclass, field
from datetime import datetime
from http import HTTPStatus
from uuid import UUID

from docmind_api.application.auth.ports import (
    Clock,
    LocalUserRepository,
    ManagedUserRepository,
    PasswordHasher,
    UserSessionBulkRevoker,
)
from docmind_api.application.auth.users import ManagedUserValidationError
from docmind_api.domain.auth.actors import AuthenticatedActor
from docmind_api.domain.auth.sessions import SessionRevocationReason
from docmind_backend_runtime.errors import ApplicationError, ConflictError


@dataclass(frozen=True, slots=True)
class ChangeOwnPasswordCommand:
    """Input for changing the current user's local password."""

    actor: AuthenticatedActor
    current_password: str = field(repr=False)
    new_password: str = field(repr=False)


@dataclass(frozen=True, slots=True)
class ChangeOwnPasswordResult:
    """Application result for a successful local password change."""

    changed: bool
    evaluated_at: datetime
    revoked_sessions: int


class LocalPasswordUnavailableError(ConflictError):
    """Raised when a user does not have local password credentials."""

    def __init__(self) -> None:
        super().__init__(
            code="LOCAL_PASSWORD_UNAVAILABLE",
            message="Local password credentials are not available for this user.",
        )


class CurrentPasswordInvalidError(ApplicationError):
    """Raised when the current password does not match local credentials."""

    def __init__(self) -> None:
        super().__init__(
            code="CURRENT_PASSWORD_INVALID",
            message="Current password is invalid.",
            status_code=HTTPStatus.BAD_REQUEST,
        )


class OwnPasswordService:
    """Application service for current-user local password changes."""

    def __init__(
        self,
        *,
        local_users: LocalUserRepository,
        users: ManagedUserRepository,
        password_hasher: PasswordHasher,
        session_revoker: UserSessionBulkRevoker,
        clock: Clock,
    ) -> None:
        self._local_users = local_users
        self._users = users
        self._password_hasher = password_hasher
        self._session_revoker = session_revoker
        self._clock = clock

    async def change_own_password(
        self,
        command: ChangeOwnPasswordCommand,
    ) -> ChangeOwnPasswordResult:
        """Change the current user's local password and revoke existing sessions."""

        user_id = UUID(command.actor.actor_id)
        if not command.new_password.strip():
            raise ManagedUserValidationError(message="New password cannot be empty.")

        user = await self._local_users.get_by_id(user_id)
        if user is None:
            await self._password_hasher.verify_password(
                command.current_password,
                self._password_hasher.verification_fallback_hash(),
            )
            raise LocalPasswordUnavailableError()

        current_password_valid = await self._password_hasher.verify_password(
            command.current_password,
            user.password_hash,
        )
        if not current_password_valid:
            raise CurrentPasswordInvalidError()

        changed_at = self._clock.now()
        password_hash = await self._password_hasher.hash_password(command.new_password)
        updated = await self._users.update_local_password_hash(
            user_id=user_id,
            password_hash=password_hash,
            updated_at=changed_at,
        )
        if not updated:
            raise LocalPasswordUnavailableError()

        revoked_sessions = await self._session_revoker.revoke_all_for_user(
            user_id,
            changed_at,
            SessionRevocationReason.PASSWORD_RESET,
        )
        return ChangeOwnPasswordResult(
            changed=True,
            evaluated_at=changed_at,
            revoked_sessions=revoked_sessions,
        )
