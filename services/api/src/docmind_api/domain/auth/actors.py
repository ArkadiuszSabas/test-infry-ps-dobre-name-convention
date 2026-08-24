"""Provider-neutral authentication actor, role, and permission models."""

from dataclasses import dataclass, field
from enum import StrEnum


class AuthProvider(StrEnum):
    """Authentication provider that identified the actor."""

    LOCAL = "local"
    ENTRA_ID = "entra_id"


class Permission(StrEnum):
    """DocMind backend permission catalog."""

    DOCUMENTS_READ = "documents.read"
    DOCUMENTS_CREATE = "documents.create"
    DOCUMENTS_REVIEW = "documents.review"
    DOCUMENTS_APPROVE = "documents.approve"
    DOCUMENTS_DELETE = "documents.delete"
    ADMIN_USERS_MANAGE = "admin.users.manage"
    ADMIN_SETTINGS_MANAGE = "admin.settings.manage"


class Role(StrEnum):
    """MVP DocMind roles."""

    ADMIN = "admin"
    REVIEWER = "reviewer"
    OPERATOR = "operator"
    VIEWER = "viewer"
    DOCUMENT_DELETER = "document_deleter"


def _empty_auth_providers() -> frozenset[AuthProvider]:
    return frozenset()


@dataclass(frozen=True, slots=True)
class AuthenticatedActor:
    """Provider-neutral authenticated actor used for backend authorization."""

    actor_id: str
    provider: AuthProvider
    tenant_id: str | None
    customer_id: str | None
    email: str | None
    roles: frozenset[Role]
    permissions: frozenset[Permission]
    auth_providers: frozenset[AuthProvider] = field(default_factory=_empty_auth_providers)

    def __post_init__(self) -> None:
        """Keep provider availability non-empty and inclusive of the session provider."""

        object.__setattr__(
            self,
            "auth_providers",
            frozenset({self.provider, *self.auth_providers}),
        )
