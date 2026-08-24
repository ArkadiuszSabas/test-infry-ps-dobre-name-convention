"""Framework-free DocMind user models."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from docmind_api.domain.auth.actors import AuthProvider, Role


class UserStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    DELETED = "deleted"


@dataclass(frozen=True, slots=True)
class DocMindUser:
    id: UUID
    display_name: str
    status: UserStatus
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        if not self.display_name.strip():
            raise ValueError("DocMind user display name cannot be empty.")
        if not _is_timezone_aware(self.created_at):
            raise ValueError("DocMind user created_at must be timezone-aware.")
        if not _is_timezone_aware(self.updated_at):
            raise ValueError("DocMind user updated_at must be timezone-aware.")
        if self.updated_at < self.created_at:
            raise ValueError("DocMind user updated_at cannot be earlier than created_at.")


@dataclass(frozen=True, slots=True)
class ManagedUser:
    """Admin-facing user read model without secret credential material."""

    id: UUID
    display_name: str
    status: UserStatus
    roles: tuple[Role, ...]
    auth_providers: tuple[AuthProvider, ...]
    email: str | None
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        if not self.display_name.strip():
            raise ValueError("Managed user display name cannot be empty.")
        if tuple(sorted(set(self.roles), key=lambda role: role.value)) != self.roles:
            raise ValueError("Managed user roles must be unique and sorted.")
        if (
            tuple(sorted(set(self.auth_providers), key=lambda provider: provider.value))
            != self.auth_providers
        ):
            raise ValueError("Managed user providers must be unique and sorted.")
        if self.email is not None and not self.email.strip():
            raise ValueError("Managed user email cannot be empty when provided.")
        if not _is_timezone_aware(self.created_at):
            raise ValueError("Managed user created_at must be timezone-aware.")
        if not _is_timezone_aware(self.updated_at):
            raise ValueError("Managed user updated_at must be timezone-aware.")
        if self.updated_at < self.created_at:
            raise ValueError("Managed user updated_at cannot be earlier than created_at.")


def _is_timezone_aware(value: datetime) -> bool:
    return value.tzinfo is not None and value.utcoffset() is not None
