"""Admin user-management use cases."""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from docmind_api.application.auth.local_accounts import (
    CreateLocalUserCommand,
    LocalUserService,
)
from docmind_api.application.auth.ports import (
    Clock,
    ManagedUserRepository,
    PasswordHasher,
    UserSessionBulkRevoker,
)
from docmind_api.domain.auth.actors import AuthenticatedActor, AuthProvider, Role
from docmind_api.domain.auth.local_accounts import LocalUserStatus, normalize_roles
from docmind_api.domain.auth.sessions import SessionRevocationReason
from docmind_api.domain.auth.users import ManagedUser, UserStatus
from docmind_backend_runtime.errors import (
    ConflictError,
    NotFoundError,
    ValidationApplicationError,
)


@dataclass(frozen=True, slots=True)
class ListUsersCommand:
    """Input for listing administratively managed users."""

    actor: AuthenticatedActor
    include_deleted: bool = False


@dataclass(frozen=True, slots=True)
class GetUserCommand:
    """Input for fetching one administratively managed user."""

    user_id: UUID
    actor: AuthenticatedActor


@dataclass(frozen=True, slots=True)
class CreateManagedLocalUserCommand:
    """Input for admin-created local username/password users."""

    login: str
    display_name: str
    plaintext_password: str = field(repr=False)
    roles: tuple[Role, ...]
    actor: AuthenticatedActor
    status: UserStatus = UserStatus.ACTIVE


@dataclass(frozen=True, slots=True)
class UpdateUserCommand:
    """Input for administratively changing editable user fields."""

    user_id: UUID
    actor: AuthenticatedActor
    display_name: str | None = None
    roles: tuple[Role, ...] | None = None
    status: UserStatus | None = None


@dataclass(frozen=True, slots=True)
class DeleteUserCommand:
    """Input for administratively deleting a user."""

    user_id: UUID
    actor: AuthenticatedActor


@dataclass(frozen=True, slots=True)
class SetUserPasswordCommand:
    """Input for administratively setting another user's local password."""

    user_id: UUID
    actor: AuthenticatedActor
    new_password: str = field(repr=False)


@dataclass(frozen=True, slots=True)
class ManagedUserResult:
    """Application result for one managed user."""

    user: ManagedUser
    evaluated_at: datetime
    revoked_sessions: int = 0


@dataclass(frozen=True, slots=True)
class ManagedUserListResult:
    """Application result for a managed user list."""

    users: tuple[ManagedUser, ...]
    evaluated_at: datetime
    total_count: int
    returned_count: int


@dataclass(frozen=True, slots=True)
class DeleteUserResult:
    """Application result for soft-deleting a user."""

    user_id: UUID
    deleted: bool
    evaluated_at: datetime
    revoked_sessions: int


@dataclass(frozen=True, slots=True)
class SetUserPasswordResult:
    """Application result for an admin password change."""

    user_id: UUID
    changed: bool
    evaluated_at: datetime
    revoked_sessions: int


class ManagedUserNotFoundError(NotFoundError):
    """Raised when a requested user is not visible in admin management."""

    def __init__(self) -> None:
        super().__init__(
            code="USER_NOT_FOUND",
            message="User not found.",
        )


class ManagedUserValidationError(ValidationApplicationError):
    """Raised when a user-management command is invalid."""

    def __init__(self, *, message: str) -> None:
        super().__init__(
            code="USER_VALIDATION_ERROR",
            message=message,
        )


class SelfUserManagementForbiddenError(ConflictError):
    """Raised when an admin would remove their own administrative access."""

    def __init__(self) -> None:
        super().__init__(
            code="SELF_USER_MANAGEMENT_FORBIDDEN",
            message="Admins cannot remove or disable their own admin access.",
        )


class SelfPasswordManagementForbiddenError(ConflictError):
    """Raised when an admin tries to bypass own-password verification."""

    def __init__(self) -> None:
        super().__init__(
            code="SELF_PASSWORD_MANAGEMENT_FORBIDDEN",
            message="Admins must use the self-service endpoint for their own password.",
        )


class ManagedUserLocalPasswordUnavailableError(ConflictError):
    """Raised when an admin password change targets a non-local account."""

    def __init__(self) -> None:
        super().__init__(
            code="LOCAL_PASSWORD_UNAVAILABLE",
            message="Local password credentials are not available for this user.",
        )


class UserAdministrationService:
    """Application service for admin-owned user lifecycle operations."""

    def __init__(
        self,
        *,
        users: ManagedUserRepository,
        local_user_service: LocalUserService,
        password_hasher: PasswordHasher,
        session_revoker: UserSessionBulkRevoker,
        clock: Clock,
    ) -> None:
        self._users = users
        self._local_user_service = local_user_service
        self._password_hasher = password_hasher
        self._session_revoker = session_revoker
        self._clock = clock

    async def list_users(self, command: ListUsersCommand) -> ManagedUserListResult:
        """List managed users ordered for admin UI display."""

        users = await self._users.list_users(include_deleted=command.include_deleted)
        return ManagedUserListResult(
            users=users,
            evaluated_at=self._clock.now(),
            total_count=len(users),
            returned_count=len(users),
        )

    async def get_user(self, command: GetUserCommand) -> ManagedUserResult:
        """Return one managed user."""

        user = await self._users.get_by_id(command.user_id)
        if user is None:
            raise ManagedUserNotFoundError()

        return ManagedUserResult(user=user, evaluated_at=self._clock.now())

    async def create_local_user(
        self,
        command: CreateManagedLocalUserCommand,
    ) -> ManagedUserResult:
        """Create a local username/password user for admin-managed deployments."""

        if command.status == UserStatus.DELETED:
            raise ManagedUserValidationError(message="New users cannot be created as deleted.")

        local_user = await self._local_user_service.create_user(
            CreateLocalUserCommand(
                login=command.login,
                display_name=command.display_name,
                plaintext_password=command.plaintext_password,
                roles=tuple(role.value for role in command.roles),
                status=LocalUserStatus(command.status.value),
            ),
        )
        user = await self._users.get_by_id(local_user.id)
        if user is None:
            raise RuntimeError("Created local user could not be loaded.")

        return ManagedUserResult(user=user, evaluated_at=self._clock.now())

    async def update_user(self, command: UpdateUserCommand) -> ManagedUserResult:
        """Update editable user fields and revoke sessions when the account is blocked."""

        if command.display_name is None and command.roles is None and command.status is None:
            raise ManagedUserValidationError(
                message="At least one user field must be provided.",
            )

        roles = _normalize_optional_roles(command.roles)
        status = command.status
        self._guard_self_destructive_update(command.actor, command.user_id, roles, status)
        if status == UserStatus.DELETED:
            raise ManagedUserValidationError(
                message="User deletion must use the delete user command.",
            )

        updated_at = self._clock.now()
        user = await self._users.update_profile(
            user_id=command.user_id,
            display_name=_stripped_optional_display_name(command.display_name),
            status=status,
            roles=roles,
            updated_at=updated_at,
        )
        if user is None:
            raise ManagedUserNotFoundError()

        revoked_sessions = 0
        if status == UserStatus.INACTIVE:
            revoked_sessions = await self._session_revoker.revoke_all_for_user(
                command.user_id,
                updated_at,
                SessionRevocationReason.ACCOUNT_DISABLED,
            )

        return ManagedUserResult(
            user=user,
            evaluated_at=updated_at,
            revoked_sessions=revoked_sessions,
        )

    async def delete_user(self, command: DeleteUserCommand) -> DeleteUserResult:
        """Soft-delete a user while preserving audit-linked records."""

        self._guard_self_delete(command.actor, command.user_id)
        return await self._delete_user_result(command.user_id, deleted_at=self._clock.now())

    async def set_user_password(
        self,
        command: SetUserPasswordCommand,
    ) -> SetUserPasswordResult:
        """Set another local user's password and revoke their active sessions."""

        self._guard_self_password_set(command.actor, command.user_id)
        if not command.new_password.strip():
            raise ManagedUserValidationError(message="New password cannot be empty.")

        user = await self._users.get_by_id(command.user_id)
        if user is None:
            raise ManagedUserNotFoundError()
        if AuthProvider.LOCAL not in user.auth_providers:
            raise ManagedUserLocalPasswordUnavailableError()

        changed_at = self._clock.now()
        password_hash = await self._password_hasher.hash_password(command.new_password)
        updated = await self._users.update_local_password_hash(
            user_id=command.user_id,
            password_hash=password_hash,
            updated_at=changed_at,
        )
        if not updated:
            raise ManagedUserLocalPasswordUnavailableError()

        revoked_sessions = await self._session_revoker.revoke_all_for_user(
            command.user_id,
            changed_at,
            SessionRevocationReason.PASSWORD_RESET,
        )
        return SetUserPasswordResult(
            user_id=command.user_id,
            changed=True,
            evaluated_at=changed_at,
            revoked_sessions=revoked_sessions,
        )

    async def _delete_user(
        self,
        user_id: UUID,
        *,
        deleted_at: datetime,
    ) -> ManagedUserResult:
        user = await self._users.soft_delete(user_id=user_id, deleted_at=deleted_at)
        if user is None:
            raise ManagedUserNotFoundError()

        revoked_sessions = await self._session_revoker.revoke_all_for_user(
            user_id,
            deleted_at,
            SessionRevocationReason.ACCOUNT_DISABLED,
        )
        return ManagedUserResult(
            user=user,
            evaluated_at=deleted_at,
            revoked_sessions=revoked_sessions,
        )

    async def _delete_user_result(
        self,
        user_id: UUID,
        *,
        deleted_at: datetime,
    ) -> DeleteUserResult:
        result = await self._delete_user(user_id, deleted_at=deleted_at)
        return DeleteUserResult(
            user_id=result.user.id,
            deleted=True,
            evaluated_at=deleted_at,
            revoked_sessions=result.revoked_sessions,
        )

    def _guard_self_destructive_update(
        self,
        actor: AuthenticatedActor,
        user_id: UUID,
        roles: tuple[Role, ...] | None,
        status: UserStatus | None,
    ) -> None:
        if str(user_id) != actor.actor_id:
            return
        if status in {UserStatus.INACTIVE, UserStatus.DELETED}:
            raise SelfUserManagementForbiddenError()
        if roles is not None:
            raise SelfUserManagementForbiddenError()

    def _guard_self_delete(self, actor: AuthenticatedActor, user_id: UUID) -> None:
        if str(user_id) == actor.actor_id:
            raise SelfUserManagementForbiddenError()

    def _guard_self_password_set(self, actor: AuthenticatedActor, user_id: UUID) -> None:
        if str(user_id) == actor.actor_id:
            raise SelfPasswordManagementForbiddenError()


def _normalize_optional_roles(roles: tuple[Role, ...] | None) -> tuple[Role, ...] | None:
    if roles is None:
        return None

    try:
        return tuple(sorted(normalize_roles(roles), key=lambda role: role.value))
    except ValueError as error:
        raise ManagedUserValidationError(message=str(error)) from error


def _stripped_optional_display_name(display_name: str | None) -> str | None:
    if display_name is None:
        return None

    stripped_display_name = display_name.strip()
    if not stripped_display_name:
        raise ManagedUserValidationError(message="User display name cannot be empty.")

    return stripped_display_name
