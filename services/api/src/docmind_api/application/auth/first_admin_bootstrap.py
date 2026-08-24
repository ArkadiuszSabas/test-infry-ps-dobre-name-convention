"""First local administrator bootstrap use case."""

from dataclasses import dataclass, field
from enum import StrEnum

from docmind_api.application.auth.local_accounts import (
    CreateLocalUserCommand,
    LocalUserService,
    LocalUserValidationError,
)
from docmind_api.application.auth.ports import FirstAdminBootstrapRepository
from docmind_api.domain.auth.actors import Role
from docmind_api.domain.auth.local_accounts import LocalUser, LocalUserStatus


@dataclass(frozen=True, slots=True)
class BootstrapFirstAdminCommand:
    """Input for controlled first local administrator bootstrap."""

    login: str
    display_name: str
    plaintext_password: str = field(repr=False)


class BootstrapFirstAdminOutcome(StrEnum):
    """Possible outcomes of first local administrator bootstrap."""

    CREATED = "created"
    ADMIN_ALREADY_EXISTS = "admin_already_exists"


@dataclass(frozen=True, slots=True)
class BootstrapFirstAdminResult:
    """Result returned by first local administrator bootstrap."""

    outcome: BootstrapFirstAdminOutcome
    user: LocalUser | None

    @classmethod
    def created(cls, user: LocalUser) -> BootstrapFirstAdminResult:
        return cls(outcome=BootstrapFirstAdminOutcome.CREATED, user=user)

    @classmethod
    def admin_already_exists(cls) -> BootstrapFirstAdminResult:
        return cls(outcome=BootstrapFirstAdminOutcome.ADMIN_ALREADY_EXISTS, user=None)


class BootstrapFirstAdminUseCase:
    """Create the first local administrator without overwriting existing admins."""

    def __init__(
        self,
        *,
        local_user_service: LocalUserService,
        repository: FirstAdminBootstrapRepository,
    ) -> None:
        self._local_user_service = local_user_service
        self._repository = repository

    async def execute(self, command: BootstrapFirstAdminCommand) -> BootstrapFirstAdminResult:
        """Create an active local admin only when no admin exists yet."""

        await self._repository.acquire_bootstrap_lock()
        if await self._repository.admin_exists():
            return BootstrapFirstAdminResult.admin_already_exists()

        if not command.plaintext_password.strip():
            raise LocalUserValidationError(message="First admin password cannot be empty.")

        user = await self._local_user_service.create_user(
            CreateLocalUserCommand(
                login=command.login,
                display_name=command.display_name,
                plaintext_password=command.plaintext_password,
                roles=(Role.ADMIN.value,),
                status=LocalUserStatus.ACTIVE,
            ),
        )
        return BootstrapFirstAdminResult.created(user)
