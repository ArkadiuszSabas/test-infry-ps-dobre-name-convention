"""Authentication repository implementations."""

from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta
from typing import Any, cast
from uuid import UUID

from sqlalchemy import case, delete, func, insert, select, update
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from docmind_api.application.auth.ports import (
    DocMindUserRepository,
    FirstAdminBootstrapRepository,
    IdentityLinkRepository,
    LocalLoginAttemptRepository,
    LocalUserRepository,
    OidcAuthTransactionRepository,
    OidcAuthTransactionStateConsumer,
    RoleAssignmentRepository,
    SessionActorContext,
    SessionActorRepository,
    UserInvitationRepository,
    UserSessionRepository,
)
from docmind_api.domain.auth.actors import AuthenticatedActor, AuthProvider, Role
from docmind_api.domain.auth.identity import IdentityLink, RoleAssignment
from docmind_api.domain.auth.invitations import (
    InvitationStatus,
    InvitationTokenHash,
    UserInvitation,
)
from docmind_api.domain.auth.local_accounts import (
    LocalLoginAttempt,
    LocalUser,
    LocalUserStatus,
    PasswordHash,
    PasswordHashParameter,
    normalize_login,
)
from docmind_api.domain.auth.oidc import OidcAuthTransaction
from docmind_api.domain.auth.policies import permissions_for_roles
from docmind_api.domain.auth.sessions import (
    SessionClientFingerprint,
    SessionRevocationReason,
    SessionTokenHash,
    UserSession,
)
from docmind_api.domain.auth.users import DocMindUser, UserStatus
from docmind_api.infrastructure.persistence.auth.actor_queries import (
    auth_providers_for_user,
)
from docmind_api.infrastructure.persistence.auth.tables import (
    identity_links_table,
    local_credentials_table,
    local_login_attempts_table,
    oidc_auth_transactions_table,
    role_assignments_table,
    user_invitations_table,
    user_sessions_table,
    users_table,
)
from docmind_api.infrastructure.persistence.sql import database_session_scope

FIRST_ADMIN_BOOTSTRAP_LOCK_ID = 30_746_001
USER_INVITATION_EMAIL_LOCK_SEED = 30_746_002


class SqlAlchemyLocalUserRepository(LocalUserRepository):
    """PostgreSQL-backed local user repository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: UUID) -> LocalUser | None:
        """Return a local user by id."""

        statement = _select_local_user().where(users_table.c.id == user_id)
        result = await self._session.execute(statement)
        row = result.mappings().one_or_none()
        if row is None:
            return None

        roles = await _roles_for_user(self._session, user_id)
        return _local_user_from_row(row, roles=roles)

    async def get_by_login(self, login: str) -> LocalUser | None:
        """Return a local user by normalized login."""

        statement = _select_local_user().where(
            local_credentials_table.c.login == normalize_login(login),
        )
        result = await self._session.execute(statement)
        row = result.mappings().one_or_none()
        if row is None:
            return None

        roles = await _roles_for_user(self._session, row["id"])
        return _local_user_from_row(row, roles=roles)

    async def add(self, user: LocalUser) -> None:
        """Store a local user in PostgreSQL."""

        await self._session.execute(
            insert(users_table).values(
                id=user.id,
                display_name=user.display_name,
                status=user.status.value,
                created_at=user.created_at,
                updated_at=user.updated_at,
            ),
        )
        await self._session.execute(
            insert(local_credentials_table).values(
                user_id=user.id,
                login=user.login,
                password_hash_algorithm=user.password_hash.algorithm,
                password_hash_parameters=[
                    {"name": parameter.name, "value": parameter.value}
                    for parameter in user.password_hash.parameters
                ],
                password_hash_value=user.password_hash.hash_value,
                created_at=user.created_at,
                updated_at=user.updated_at,
            ),
        )
        await _add_role_assignments(
            self._session,
            tuple(
                RoleAssignment(
                    user_id=user.id,
                    role=role,
                    source_provider=AuthProvider.LOCAL,
                    identity_link_id=None,
                    created_at=user.created_at,
                    updated_at=user.updated_at,
                )
                for role in user.roles
            ),
        )


class SqlAlchemyFirstAdminBootstrapRepository(FirstAdminBootstrapRepository):
    """PostgreSQL-backed first-admin bootstrap guard."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def acquire_bootstrap_lock(self) -> None:
        """Acquire the transaction-scoped bootstrap lock."""

        await self._session.execute(
            select(func.pg_advisory_xact_lock(FIRST_ADMIN_BOOTSTRAP_LOCK_ID)),
        )

    async def admin_exists(self) -> bool:
        """Return whether any DocMind admin role already exists."""

        statement = (
            select(role_assignments_table.c.user_id)
            .where(role_assignments_table.c.role == Role.ADMIN.value)
            .limit(1)
        )
        result = await self._session.execute(statement)
        return result.first() is not None


class SqlAlchemyLocalLoginAttemptRepository(LocalLoginAttemptRepository):
    """PostgreSQL-backed local login attempt repository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_login(self, login: str) -> LocalLoginAttempt | None:
        """Return failed login attempt state by normalized login."""

        statement = select(local_login_attempts_table).where(
            local_login_attempts_table.c.login == normalize_login(login),
        )
        result = await self._session.execute(statement)
        row = result.mappings().one_or_none()
        if row is None:
            return None

        return _local_login_attempt_from_row(row)

    async def record_failed_attempt(
        self,
        *,
        login: str,
        failed_at: datetime,
        max_failed_attempts: int,
        cooldown: timedelta,
    ) -> LocalLoginAttempt:
        """Atomically record a failed login attempt and return the updated state."""

        normalized_login = normalize_login(login)
        locked_until = failed_at + cooldown
        lock_on_insert = locked_until if max_failed_attempts <= 1 else None
        cooldown_expired = local_login_attempts_table.c.locked_until.is_not(None) & (
            local_login_attempts_table.c.locked_until <= failed_at
        )
        next_failed_attempt_count = case(
            (cooldown_expired, 1),
            else_=local_login_attempts_table.c.failed_attempt_count + 1,
        )
        next_locked_until = case(
            (next_failed_attempt_count >= max_failed_attempts, locked_until),
            else_=None,
        )

        statement = postgresql_insert(local_login_attempts_table).values(
            login=normalized_login,
            failed_attempt_count=1,
            last_failed_at=failed_at,
            locked_until=lock_on_insert,
        )
        result = await self._session.execute(
            statement.on_conflict_do_update(
                index_elements=[local_login_attempts_table.c.login],
                set_={
                    "failed_attempt_count": next_failed_attempt_count,
                    "last_failed_at": failed_at,
                    "locked_until": next_locked_until,
                },
            ).returning(local_login_attempts_table),
        )
        return _local_login_attempt_from_row(result.mappings().one())

    async def reset(self, login: str) -> None:
        """Clear failed login attempt state for a normalized login."""

        await self._session.execute(
            delete(local_login_attempts_table).where(
                local_login_attempts_table.c.login == normalize_login(login),
            ),
        )


class SqlAlchemyLocalLoginAttemptRecorder:
    """Durably records failed local login attempts outside request rollbacks."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def record_failed_attempt(
        self,
        *,
        login: str,
        failed_at: datetime,
        max_failed_attempts: int,
        cooldown: timedelta,
    ) -> LocalLoginAttempt:
        """Record a failed attempt in a committed transaction."""

        async with database_session_scope(self._session_factory) as session:
            repository = SqlAlchemyLocalLoginAttemptRepository(session)
            return await repository.record_failed_attempt(
                login=login,
                failed_at=failed_at,
                max_failed_attempts=max_failed_attempts,
                cooldown=cooldown,
            )


class SqlAlchemyDocMindUserRepository(DocMindUserRepository):
    """PostgreSQL-backed DocMind user repository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: UUID) -> DocMindUser | None:
        """Return a DocMind user by id."""

        statement = select(users_table).where(users_table.c.id == user_id)
        result = await self._session.execute(statement)
        row = result.mappings().one_or_none()
        if row is None:
            return None

        return _docmind_user_from_row(row)

    async def add(self, user: DocMindUser) -> None:
        """Store a DocMind user in PostgreSQL."""

        await self._session.execute(
            insert(users_table).values(
                id=user.id,
                display_name=user.display_name,
                status=user.status.value,
                created_at=user.created_at,
                updated_at=user.updated_at,
            ),
        )


class SqlAlchemyUserSessionRepository(UserSessionRepository):
    """PostgreSQL-backed browser session repository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, session_id: UUID) -> UserSession | None:
        """Return a browser session by id."""

        statement = select(user_sessions_table).where(
            user_sessions_table.c.id == session_id,
        )
        result = await self._session.execute(statement)
        row = result.mappings().one_or_none()
        if row is None:
            return None

        return _user_session_from_row(row)

    async def get_by_token_hash(self, token_hash: SessionTokenHash) -> UserSession | None:
        """Return a browser session by persisted token hash."""

        statement = select(user_sessions_table).where(
            user_sessions_table.c.token_hash == token_hash.value,
        )
        result = await self._session.execute(statement)
        row = result.mappings().one_or_none()
        if row is None:
            return None

        return _user_session_from_row(row)

    async def list_for_user(self, user_id: UUID) -> tuple[UserSession, ...]:
        """Return browser sessions for a user, newest activity first."""

        statement = (
            select(user_sessions_table)
            .where(user_sessions_table.c.user_id == user_id)
            .order_by(
                user_sessions_table.c.last_seen_at.desc(),
                user_sessions_table.c.created_at.desc(),
            )
        )
        result = await self._session.execute(statement)
        return tuple(_user_session_from_row(row) for row in result.mappings())

    async def add(self, session: UserSession) -> None:
        """Store a browser session in PostgreSQL."""

        await self._session.execute(
            insert(user_sessions_table).values(
                id=session.id,
                user_id=session.user_id,
                token_hash=session.token_hash.value,
                created_at=session.created_at,
                last_seen_at=session.last_seen_at,
                expires_at=session.expires_at,
                revoked_at=session.revoked_at,
                revoked_reason=session.revoked_reason.value
                if session.revoked_reason is not None
                else None,
                auth_provider=session.auth_provider.value,
                identity_link_id=session.identity_link_id,
                client_label=session.client_label,
                client_fingerprint=session.client_fingerprint.value
                if session.client_fingerprint is not None
                else None,
            ),
        )

    async def touch(self, session_id: UUID, last_seen_at: datetime) -> None:
        """Update a session last-seen timestamp."""

        statement = (
            update(user_sessions_table)
            .where(user_sessions_table.c.id == session_id)
            .values(last_seen_at=last_seen_at)
        )
        await self._session.execute(statement)

    async def revoke(
        self,
        session_id: UUID,
        revoked_at: datetime,
        reason: SessionRevocationReason,
    ) -> bool:
        """Mark a browser session as revoked."""

        statement = (
            update(user_sessions_table)
            .where(
                user_sessions_table.c.id == session_id,
                user_sessions_table.c.revoked_at.is_(None),
            )
            .values(revoked_at=revoked_at, revoked_reason=reason.value)
            .returning(user_sessions_table.c.id)
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none() is not None


class SqlAlchemySessionActorRepository(SessionActorRepository):
    """PostgreSQL-backed actor lookup for active browser sessions."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_actor_for_session(
        self,
        session_context: SessionActorContext,
    ) -> AuthenticatedActor | None:
        """Return the actor represented by an active session context."""

        statement = select(users_table).where(users_table.c.id == session_context.user_id)
        result = await self._session.execute(statement)
        row = result.mappings().one_or_none()
        if row is None:
            return None

        if UserStatus(row["status"]) != UserStatus.ACTIVE:
            return None

        roles = await _roles_for_user(self._session, session_context.user_id)
        email = await _email_for_session_context(self._session, session_context)
        auth_providers = await auth_providers_for_user(
            self._session,
            session_context.user_id,
        )
        return AuthenticatedActor(
            actor_id=str(row["id"]),
            provider=session_context.auth_provider,
            tenant_id=None,
            customer_id=None,
            email=email,
            roles=roles,
            permissions=permissions_for_roles(roles),
            auth_providers=auth_providers,
        )


class SqlAlchemyIdentityLinkRepository(IdentityLinkRepository):
    """PostgreSQL-backed external identity link repository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_provider_identity(
        self,
        *,
        provider: AuthProvider,
        issuer: str,
        tenant_id: str,
        subject: str,
    ) -> IdentityLink | None:
        """Return an identity link by provider-owned identity."""

        statement = select(identity_links_table).where(
            identity_links_table.c.provider == provider.value,
            identity_links_table.c.issuer == issuer,
            identity_links_table.c.tenant_id == tenant_id,
            identity_links_table.c.subject == subject,
        )
        result = await self._session.execute(statement)
        row = result.mappings().one_or_none()
        if row is None:
            return None

        return _identity_link_from_row(row)

    async def add(self, identity_link: IdentityLink) -> None:
        """Store an external identity link in PostgreSQL."""

        await self._session.execute(
            insert(identity_links_table).values(
                id=identity_link.id,
                user_id=identity_link.user_id,
                provider=identity_link.provider.value,
                issuer=identity_link.issuer,
                tenant_id=identity_link.tenant_id,
                subject=identity_link.subject,
                email=identity_link.email,
                created_at=identity_link.created_at,
                updated_at=identity_link.updated_at,
            ),
        )


class SqlAlchemyRoleAssignmentRepository(RoleAssignmentRepository):
    """PostgreSQL-backed DocMind role assignment repository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_roles_for_user(self, user_id: UUID) -> frozenset[Role]:
        """Return DocMind roles assigned to a user."""

        return await _roles_for_user(self._session, user_id)

    async def add_many(self, role_assignments: tuple[RoleAssignment, ...]) -> None:
        """Store DocMind role assignments in PostgreSQL."""

        await _add_role_assignments(self._session, role_assignments)

    async def replace_for_identity_link(
        self,
        *,
        user_id: UUID,
        identity_link_id: UUID,
        role_assignments: tuple[RoleAssignment, ...],
    ) -> None:
        """Replace Entra-sourced role assignments for one identity link."""

        await self._session.execute(
            delete(role_assignments_table).where(
                role_assignments_table.c.user_id == user_id,
                role_assignments_table.c.source_provider == AuthProvider.ENTRA_ID.value,
                role_assignments_table.c.identity_link_id == identity_link_id,
            ),
        )
        await _add_role_assignments(self._session, role_assignments)


class SqlAlchemyOidcAuthTransactionRepository(OidcAuthTransactionRepository):
    """PostgreSQL-backed OIDC auth transaction repository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, transaction: OidcAuthTransaction) -> None:
        """Store a short-lived OIDC login transaction."""

        await self._session.execute(
            insert(oidc_auth_transactions_table).values(
                state_hash=transaction.state_hash,
                nonce_hash=transaction.nonce_hash,
                browser_binding_hash=transaction.browser_binding_hash,
                pkce_verifier=transaction.pkce_verifier,
                redirect_uri=transaction.redirect_uri,
                redirect_target=transaction.redirect_target,
                created_at=transaction.created_at,
                expires_at=transaction.expires_at,
                used_at=transaction.used_at,
            ),
        )

    async def get_by_state_hash(self, state_hash: str) -> OidcAuthTransaction | None:
        """Return an OIDC login transaction by persisted state hash."""

        statement = select(oidc_auth_transactions_table).where(
            oidc_auth_transactions_table.c.state_hash == state_hash,
        )
        result = await self._session.execute(statement)
        row = result.mappings().one_or_none()
        if row is None:
            return None

        return _oidc_auth_transaction_from_row(row)

    async def mark_used(self, state_hash: str, used_at: datetime) -> bool:
        """Mark an unused OIDC login transaction as consumed."""

        statement = (
            update(oidc_auth_transactions_table)
            .where(
                oidc_auth_transactions_table.c.state_hash == state_hash,
                oidc_auth_transactions_table.c.used_at.is_(None),
            )
            .values(used_at=used_at)
            .returning(oidc_auth_transactions_table.c.state_hash)
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none() is not None


class SqlAlchemyOidcAuthTransactionStateConsumer(OidcAuthTransactionStateConsumer):
    """Consumes OIDC state in a separate DB transaction before callback IO."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def mark_used(self, state_hash: str, used_at: datetime) -> bool:
        """Mark an unused OIDC state as consumed and commit that change immediately."""

        async with database_session_scope(self._session_factory) as session:
            repository = SqlAlchemyOidcAuthTransactionRepository(session)
            return await repository.mark_used(state_hash, used_at)


class SqlAlchemyUserInvitationRepository(UserInvitationRepository):
    """PostgreSQL-backed user invitation repository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, invitation_id: UUID) -> UserInvitation | None:
        """Return an invitation by id."""

        result = await self._session.execute(
            select(user_invitations_table).where(
                user_invitations_table.c.id == invitation_id,
            ),
        )
        row = result.mappings().one_or_none()
        if row is None:
            return None

        return _user_invitation_from_row(row)

    async def acquire_pending_email_creation_slot(
        self,
        *,
        email: str,
        evaluated_at: datetime,
    ) -> bool:
        """Serialize pending invitation creation for one normalized email."""

        await self._session.execute(
            select(
                func.pg_advisory_xact_lock(
                    func.hashtextextended(email, USER_INVITATION_EMAIL_LOCK_SEED),
                ),
            ),
        )
        return (await self.get_pending_by_email(email=email, evaluated_at=evaluated_at)) is None

    async def get_pending_by_email(
        self,
        *,
        email: str,
        evaluated_at: datetime,
    ) -> UserInvitation | None:
        """Return an active pending invitation for a normalized email."""

        result = await self._session.execute(
            select(user_invitations_table).where(
                user_invitations_table.c.email == email,
                user_invitations_table.c.status == InvitationStatus.PENDING.value,
                user_invitations_table.c.expires_at > evaluated_at,
            ),
        )
        row = result.mappings().one_or_none()
        if row is None:
            return None

        return _user_invitation_from_row(row)

    async def list_pending(self, *, evaluated_at: datetime) -> tuple[UserInvitation, ...]:
        """Return active pending invitations newest first."""

        result = await self._session.execute(
            select(user_invitations_table)
            .where(
                user_invitations_table.c.status == InvitationStatus.PENDING.value,
                user_invitations_table.c.expires_at > evaluated_at,
            )
            .order_by(
                user_invitations_table.c.created_at.desc(),
                user_invitations_table.c.email.asc(),
            ),
        )
        return tuple(_user_invitation_from_row(row) for row in result.mappings())

    async def add(self, invitation: UserInvitation) -> None:
        """Store an invitation in PostgreSQL."""

        await self._session.execute(
            insert(user_invitations_table).values(
                id=invitation.id,
                email=invitation.email,
                roles=[role.value for role in invitation.roles],
                token_hash=invitation.token_hash.value,
                status=invitation.status.value,
                created_by_user_id=invitation.created_by_user_id,
                created_at=invitation.created_at,
                updated_at=invitation.updated_at,
                expires_at=invitation.expires_at,
                cancelled_at=invitation.cancelled_at,
                cancelled_by_user_id=invitation.cancelled_by_user_id,
                accepted_at=invitation.accepted_at,
                accepted_by_user_id=invitation.accepted_by_user_id,
            ),
        )

    async def cancel(
        self,
        *,
        invitation_id: UUID,
        cancelled_at: datetime,
        cancelled_by_user_id: UUID,
    ) -> UserInvitation | None:
        """Mark a pending invitation as cancelled."""

        statement = (
            update(user_invitations_table)
            .where(
                user_invitations_table.c.id == invitation_id,
                user_invitations_table.c.status == InvitationStatus.PENDING.value,
                user_invitations_table.c.expires_at > cancelled_at,
            )
            .values(
                status=InvitationStatus.CANCELLED.value,
                updated_at=cancelled_at,
                cancelled_at=cancelled_at,
                cancelled_by_user_id=cancelled_by_user_id,
            )
            .returning(user_invitations_table)
        )
        result = await self._session.execute(statement)
        row = result.mappings().one_or_none()
        if row is None:
            return None

        return _user_invitation_from_row(row)


def _select_local_user() -> Any:
    return (
        select(
            users_table.c.id,
            local_credentials_table.c.login,
            users_table.c.display_name,
            users_table.c.status,
            local_credentials_table.c.password_hash_algorithm,
            local_credentials_table.c.password_hash_parameters,
            local_credentials_table.c.password_hash_value,
            users_table.c.created_at,
            users_table.c.updated_at,
        )
        .select_from(users_table)
        .join(local_credentials_table, local_credentials_table.c.user_id == users_table.c.id)
    )


def _local_user_from_row(row: Mapping[Any, Any], *, roles: frozenset[Role]) -> LocalUser:
    password_parameters = cast(
        Sequence[Mapping[str, str]],
        row["password_hash_parameters"],
    )

    return LocalUser(
        id=row["id"],
        login=row["login"],
        display_name=row["display_name"],
        status=LocalUserStatus(row["status"]),
        roles=tuple(sorted(roles, key=lambda role: role.value)),
        password_hash=PasswordHash(
            algorithm=row["password_hash_algorithm"],
            parameters=tuple(
                PasswordHashParameter(name=parameter["name"], value=parameter["value"])
                for parameter in password_parameters
            ),
            hash_value=row["password_hash_value"],
        ),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _local_login_attempt_from_row(row: Mapping[Any, Any]) -> LocalLoginAttempt:
    return LocalLoginAttempt(
        login=row["login"],
        failed_attempt_count=row["failed_attempt_count"],
        last_failed_at=row["last_failed_at"],
        locked_until=row["locked_until"],
    )


def _user_session_from_row(row: Mapping[Any, Any]) -> UserSession:
    return UserSession(
        id=row["id"],
        user_id=row["user_id"],
        token_hash=SessionTokenHash(row["token_hash"]),
        created_at=row["created_at"],
        last_seen_at=row["last_seen_at"],
        expires_at=row["expires_at"],
        revoked_at=row["revoked_at"],
        revoked_reason=SessionRevocationReason(row["revoked_reason"])
        if row["revoked_reason"] is not None
        else None,
        auth_provider=AuthProvider(row["auth_provider"]),
        identity_link_id=row["identity_link_id"],
        client_label=row["client_label"],
        client_fingerprint=SessionClientFingerprint(row["client_fingerprint"])
        if row["client_fingerprint"] is not None
        else None,
    )


async def _roles_for_user(session: AsyncSession, user_id: UUID) -> frozenset[Role]:
    statement = select(role_assignments_table.c.role).where(
        role_assignments_table.c.user_id == user_id,
    )
    result = await session.execute(statement)
    return frozenset(Role(row.role) for row in result)


async def _email_for_session_context(
    session: AsyncSession,
    session_context: SessionActorContext,
) -> str | None:
    if session_context.auth_provider == AuthProvider.LOCAL:
        statement = select(local_credentials_table.c.login).where(
            local_credentials_table.c.user_id == session_context.user_id,
        )
        result = await session.execute(statement)
        return result.scalar_one_or_none()

    if session_context.identity_link_id is None:
        return None

    statement = select(identity_links_table.c.email).where(
        identity_links_table.c.id == session_context.identity_link_id,
        identity_links_table.c.user_id == session_context.user_id,
    )
    result = await session.execute(statement)
    return result.scalar_one_or_none()


async def _add_role_assignments(
    session: AsyncSession,
    role_assignments: tuple[RoleAssignment, ...],
) -> None:
    if not role_assignments:
        return

    values = [
        {
            "user_id": role_assignment.user_id,
            "role": role_assignment.role.value,
            "source_provider": role_assignment.source_provider.value,
            "identity_link_id": role_assignment.identity_link_id,
            "created_at": role_assignment.created_at,
            "updated_at": role_assignment.updated_at,
        }
        for role_assignment in role_assignments
    ]
    statement = postgresql_insert(role_assignments_table).values(values)
    await session.execute(
        statement.on_conflict_do_nothing(
            index_elements=[
                role_assignments_table.c.user_id,
                role_assignments_table.c.role,
                role_assignments_table.c.source_provider,
            ],
        ),
    )


def _identity_link_from_row(row: Mapping[Any, Any]) -> IdentityLink:
    return IdentityLink(
        id=row["id"],
        user_id=row["user_id"],
        provider=AuthProvider(row["provider"]),
        issuer=row["issuer"],
        tenant_id=row["tenant_id"],
        subject=row["subject"],
        email=row["email"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _docmind_user_from_row(row: Mapping[Any, Any]) -> DocMindUser:
    return DocMindUser(
        id=row["id"],
        display_name=row["display_name"],
        status=UserStatus(row["status"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _oidc_auth_transaction_from_row(row: Mapping[Any, Any]) -> OidcAuthTransaction:
    return OidcAuthTransaction(
        state_hash=row["state_hash"],
        nonce_hash=row["nonce_hash"],
        browser_binding_hash=row["browser_binding_hash"],
        pkce_verifier=row["pkce_verifier"],
        redirect_uri=row["redirect_uri"],
        redirect_target=row["redirect_target"],
        created_at=row["created_at"],
        expires_at=row["expires_at"],
        used_at=row["used_at"],
    )


def _user_invitation_from_row(row: Mapping[Any, Any]) -> UserInvitation:
    roles = cast(Sequence[str], row["roles"])
    return UserInvitation(
        id=row["id"],
        email=row["email"],
        roles=tuple(sorted((Role(role) for role in roles), key=lambda role: role.value)),
        token_hash=InvitationTokenHash(row["token_hash"]),
        status=InvitationStatus(row["status"]),
        created_by_user_id=row["created_by_user_id"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        expires_at=row["expires_at"],
        cancelled_at=row["cancelled_at"],
        cancelled_by_user_id=row["cancelled_by_user_id"],
        accepted_at=row["accepted_at"],
        accepted_by_user_id=row["accepted_by_user_id"],
    )
