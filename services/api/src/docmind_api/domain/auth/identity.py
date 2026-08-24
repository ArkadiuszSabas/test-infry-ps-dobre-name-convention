"""Framework-free DocMind identity link and role assignment models."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from docmind_api.domain.auth.actors import AuthProvider, Role


@dataclass(frozen=True, slots=True)
class IdentityLink:
    """Durable binding from an external identity provider to a DocMind user."""

    id: UUID
    user_id: UUID
    provider: AuthProvider
    issuer: str
    tenant_id: str
    subject: str
    email: str | None
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        if self.provider == AuthProvider.LOCAL:
            raise ValueError("Local credentials are not identity links.")
        if not self.issuer.strip():
            raise ValueError("Identity link issuer cannot be empty.")
        if not self.tenant_id.strip():
            raise ValueError("Identity link tenant_id cannot be empty.")
        if not self.subject.strip():
            raise ValueError("Identity link subject cannot be empty.")
        if self.email is not None and not self.email.strip():
            raise ValueError("Identity link email cannot be empty when provided.")
        _validate_audit_timestamps(
            created_at=self.created_at,
            updated_at=self.updated_at,
            model_name="Identity link",
        )


@dataclass(frozen=True, slots=True)
class RoleAssignment:
    """Durable DocMind role assigned to a user."""

    user_id: UUID
    role: Role
    source_provider: AuthProvider
    identity_link_id: UUID | None
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        if self.source_provider == AuthProvider.LOCAL and self.identity_link_id is not None:
            raise ValueError("Local role assignments cannot reference an identity link.")
        if self.source_provider != AuthProvider.LOCAL and self.identity_link_id is None:
            raise ValueError("External role assignments require an identity link.")
        _validate_audit_timestamps(
            created_at=self.created_at,
            updated_at=self.updated_at,
            model_name="Role assignment",
        )


def _validate_audit_timestamps(
    *,
    created_at: datetime,
    updated_at: datetime,
    model_name: str,
) -> None:
    if not _is_timezone_aware(created_at):
        raise ValueError(f"{model_name} created_at must be timezone-aware.")
    if not _is_timezone_aware(updated_at):
        raise ValueError(f"{model_name} updated_at must be timezone-aware.")
    if updated_at < created_at:
        raise ValueError(f"{model_name} updated_at cannot be earlier than created_at.")


def _is_timezone_aware(value: datetime) -> bool:
    return value.tzinfo is not None and value.utcoffset() is not None
