"""Repository and persistence side-effect ports for auth use cases."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol
from uuid import UUID

from docmind_api.domain.auth.actors import AuthenticatedActor, AuthProvider, Role
from docmind_api.domain.auth.identity import IdentityLink, RoleAssignment
from docmind_api.domain.auth.invitations import UserInvitation
from docmind_api.domain.auth.local_accounts import LocalLoginAttempt, LocalUser, PasswordHash
from docmind_api.domain.auth.oidc import OidcAuthTransaction
from docmind_api.domain.auth.sessions import (
    RefreshTokenHash,
    SessionRefreshToken,
    SessionRevocationReason,
    SessionTokenHash,
    UserSession,
)
from docmind_api.domain.auth.users import DocMindUser, ManagedUser, UserStatus


@dataclass(frozen=True, slots=True)
class SessionActorContext:
    user_id: UUID
    auth_provider: AuthProvider
    identity_link_id: UUID | None


class LocalUserRepository(Protocol):
    """Port implemented by local user persistence adapters."""

    async def get_by_id(self, user_id: UUID) -> LocalUser | None: ...

    async def get_by_login(self, login: str) -> LocalUser | None: ...

    async def add(self, user: LocalUser) -> None: ...


class LocalLoginAttemptRepository(Protocol):
    """Port implemented by local login attempt persistence adapters."""

    async def get_by_login(self, login: str) -> LocalLoginAttempt | None: ...

    async def reset(self, login: str) -> None: ...


class LocalLoginAttemptRecorder(Protocol):
    """Port for durably recording failed local login attempts."""

    async def record_failed_attempt(
        self,
        *,
        login: str,
        failed_at: datetime,
        max_failed_attempts: int,
        cooldown: timedelta,
    ) -> LocalLoginAttempt: ...


class FirstAdminBootstrapRepository(Protocol):
    """Port for checking whether first-admin bootstrap may create an admin."""

    async def acquire_bootstrap_lock(self) -> None: ...

    async def admin_exists(self) -> bool: ...


class DocMindUserRepository(Protocol):
    """Port implemented by DocMind user persistence adapters."""

    async def get_by_id(self, user_id: UUID) -> DocMindUser | None: ...

    async def add(self, user: DocMindUser) -> None: ...


class ManagedUserRepository(Protocol):
    """Port implemented by admin user-management persistence adapters."""

    async def list_users(
        self,
        *,
        include_deleted: bool = False,
    ) -> tuple[ManagedUser, ...]: ...

    async def get_by_id(
        self,
        user_id: UUID,
        *,
        include_deleted: bool = False,
    ) -> ManagedUser | None: ...

    async def update_profile(
        self,
        *,
        user_id: UUID,
        display_name: str | None,
        status: UserStatus | None,
        roles: tuple[Role, ...] | None,
        updated_at: datetime,
    ) -> ManagedUser | None: ...

    async def soft_delete(
        self,
        *,
        user_id: UUID,
        deleted_at: datetime,
    ) -> ManagedUser | None: ...

    async def update_local_password_hash(
        self,
        *,
        user_id: UUID,
        password_hash: PasswordHash,
        updated_at: datetime,
    ) -> bool: ...


class SessionActorRepository(Protocol):
    """Port implemented by adapters that map session contexts to actors."""

    async def get_actor_for_session(
        self,
        session_context: SessionActorContext,
    ) -> AuthenticatedActor | None: ...


class IdentityLinkRepository(Protocol):
    """Port implemented by external identity link persistence adapters."""

    async def get_by_provider_identity(
        self,
        *,
        provider: AuthProvider,
        issuer: str,
        tenant_id: str,
        subject: str,
    ) -> IdentityLink | None: ...

    async def add(self, identity_link: IdentityLink) -> None: ...


class RoleAssignmentRepository(Protocol):
    """Port implemented by DocMind role assignment persistence adapters."""

    async def get_roles_for_user(self, user_id: UUID) -> frozenset[Role]: ...

    async def add_many(self, role_assignments: tuple[RoleAssignment, ...]) -> None: ...

    async def replace_for_identity_link(
        self,
        *,
        user_id: UUID,
        identity_link_id: UUID,
        role_assignments: tuple[RoleAssignment, ...],
    ) -> None: ...


class UserInvitationRepository(Protocol):
    """Port implemented by admin invitation persistence adapters."""

    async def get_by_id(self, invitation_id: UUID) -> UserInvitation | None: ...

    async def acquire_pending_email_creation_slot(
        self,
        *,
        email: str,
        evaluated_at: datetime,
    ) -> bool: ...

    async def get_pending_by_email(
        self,
        *,
        email: str,
        evaluated_at: datetime,
    ) -> UserInvitation | None: ...

    async def list_pending(self, *, evaluated_at: datetime) -> tuple[UserInvitation, ...]: ...

    async def add(self, invitation: UserInvitation) -> None: ...

    async def cancel(
        self,
        *,
        invitation_id: UUID,
        cancelled_at: datetime,
        cancelled_by_user_id: UUID,
    ) -> UserInvitation | None: ...


class OidcAuthTransactionRepository(Protocol):
    """Port implemented by OIDC auth transaction persistence adapters."""

    async def add(self, transaction: OidcAuthTransaction) -> None: ...

    async def get_by_state_hash(self, state_hash: str) -> OidcAuthTransaction | None: ...

    async def mark_used(self, state_hash: str, used_at: datetime) -> bool: ...


class OidcAuthTransactionStateConsumer(Protocol):
    """Port for durably consuming OIDC auth transaction state before callback IO."""

    async def mark_used(self, state_hash: str, used_at: datetime) -> bool: ...


class UserSessionRepository(Protocol):
    """Port implemented by browser session persistence adapters."""

    async def get_by_id(self, session_id: UUID) -> UserSession | None: ...

    async def get_by_token_hash(self, token_hash: SessionTokenHash) -> UserSession | None: ...

    async def list_for_user(self, user_id: UUID) -> tuple[UserSession, ...]: ...

    async def add(self, session: UserSession) -> None: ...

    async def touch(self, session_id: UUID, last_seen_at: datetime) -> None: ...

    async def revoke(
        self,
        session_id: UUID,
        revoked_at: datetime,
        reason: SessionRevocationReason,
    ) -> bool: ...


class RefreshTokenRepository(Protocol):
    """Port implemented by refresh token persistence adapters."""

    async def get_by_token_hash(
        self,
        token_hash: RefreshTokenHash,
    ) -> SessionRefreshToken | None: ...

    async def add(self, refresh_token: SessionRefreshToken) -> None: ...

    async def mark_rotated(self, refresh_token_id: UUID, rotated_at: datetime) -> bool: ...

    async def mark_reused(self, refresh_token_id: UUID, reused_at: datetime) -> None: ...

    async def revoke_family(self, family_id: UUID, revoked_at: datetime) -> None: ...


class RefreshTokenFamilyRevoker(Protocol):
    """Port for revoking refresh families and sessions as a durable security side effect."""

    async def revoke_family(
        self,
        family_id: UUID,
        revoked_at: datetime,
        reason: SessionRevocationReason,
    ) -> bool: ...

    async def record_reuse_and_revoke_family(
        self,
        *,
        refresh_token_id: UUID,
        family_id: UUID,
        reused_at: datetime,
    ) -> None: ...

    async def revoke_session_family(
        self,
        session_id: UUID,
        revoked_at: datetime,
        reason: SessionRevocationReason,
    ) -> bool: ...


class UserSessionBulkRevoker(Protocol):
    """Port for revoking all browser sessions for one user."""

    async def revoke_all_for_user(
        self,
        user_id: UUID,
        revoked_at: datetime,
        reason: SessionRevocationReason,
    ) -> int: ...
