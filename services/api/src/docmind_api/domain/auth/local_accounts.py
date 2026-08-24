"""Framework-free local account domain models."""

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from docmind_api.domain.auth.actors import Role


class LocalUserStatus(StrEnum):
    """Lifecycle status for local users."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    DELETED = "deleted"


@dataclass(frozen=True, slots=True)
class PasswordHashParameter:
    """One persisted password hashing parameter."""

    name: str
    value: str

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Password hash parameter name cannot be empty.")
        if not self.value.strip():
            raise ValueError("Password hash parameter value cannot be empty.")


@dataclass(frozen=True, slots=True)
class PasswordHash:
    """Persisted password hash with algorithm metadata."""

    algorithm: str
    parameters: tuple[PasswordHashParameter, ...]
    hash_value: str = field(repr=False)

    def __post_init__(self) -> None:
        if not self.algorithm.strip():
            raise ValueError("Password hash algorithm cannot be empty.")
        if not self.parameters:
            raise ValueError("Password hash parameters cannot be empty.")
        if not self.hash_value.strip():
            raise ValueError("Password hash value cannot be empty.")

    def parameter_map(self) -> dict[str, str]:
        """Return parameters as a dictionary for persistence adapters."""

        return {parameter.name: parameter.value for parameter in self.parameters}


@dataclass(frozen=True, slots=True)
class LocalUser:
    """Local user account for deployments without an external identity provider."""

    id: UUID
    login: str
    display_name: str
    status: LocalUserStatus
    roles: tuple[Role, ...]
    password_hash: PasswordHash = field(repr=False)
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        if self.login != normalize_login(self.login):
            raise ValueError("Local user login must be normalized.")
        if not self.display_name.strip():
            raise ValueError("Local user display name cannot be empty.")
        if self.roles != normalize_roles(self.roles):
            raise ValueError("Local user roles must be normalized.")
        if not _is_timezone_aware(self.created_at):
            raise ValueError("Local user created_at must be timezone-aware.")
        if not _is_timezone_aware(self.updated_at):
            raise ValueError("Local user updated_at must be timezone-aware.")
        if self.updated_at < self.created_at:
            raise ValueError("Local user updated_at cannot be earlier than created_at.")

    @property
    def is_active(self) -> bool:
        """Return whether the account can authenticate."""

        return self.status == LocalUserStatus.ACTIVE


@dataclass(frozen=True, slots=True)
class LocalLoginAttempt:
    """Failed local login attempt state for MVP brute-force hardening."""

    login: str
    failed_attempt_count: int
    last_failed_at: datetime
    locked_until: datetime | None = None

    def __post_init__(self) -> None:
        if self.login != normalize_login(self.login):
            raise ValueError("Local login attempt login must be normalized.")
        if self.failed_attempt_count < 1:
            raise ValueError("Local login attempt count must be positive.")
        if not _is_timezone_aware(self.last_failed_at):
            raise ValueError("Local login attempt last_failed_at must be timezone-aware.")
        if self.locked_until is not None:
            if not _is_timezone_aware(self.locked_until):
                raise ValueError("Local login attempt locked_until must be timezone-aware.")
            if self.locked_until < self.last_failed_at:
                raise ValueError("Local login attempt locked_until cannot be before failure time.")

    def is_locked_at(self, timestamp: datetime) -> bool:
        """Return whether this login is still under cooldown at a timestamp."""

        return self.locked_until is not None and self.locked_until > timestamp


def normalize_login(login: str) -> str:
    """Normalize a local login or email identifier."""

    normalized = login.strip().lower()
    if not normalized:
        raise ValueError("Local user login cannot be empty.")
    return normalized


def normalize_roles(roles: Iterable[Role | str]) -> tuple[Role, ...]:
    """Normalize roles while preserving their first-seen order."""

    normalized_roles: list[Role] = []
    seen_roles: set[Role] = set()

    for role in roles:
        normalized_role_name = role.value if isinstance(role, Role) else role.strip().lower()
        if not normalized_role_name:
            raise ValueError("Local user role cannot be empty.")
        try:
            normalized_role = Role(normalized_role_name)
        except ValueError:
            raise ValueError("Local user role is not supported.") from None
        if normalized_role not in seen_roles:
            normalized_roles.append(normalized_role)
            seen_roles.add(normalized_role)

    if not normalized_roles:
        raise ValueError("Local user must have at least one role.")

    return tuple(normalized_roles)


def _is_timezone_aware(value: datetime) -> bool:
    return value.tzinfo is not None and value.utcoffset() is not None
