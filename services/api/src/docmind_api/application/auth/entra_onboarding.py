"""Entra ID identity onboarding and linking use cases."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from docmind_api.application.auth.entra_claims import MappedEntraIdentity
from docmind_api.application.auth.ports import (
    Clock,
    DocMindUserIdGenerator,
    DocMindUserRepository,
    IdentityLinkIdGenerator,
    IdentityLinkRepository,
    RoleAssignmentRepository,
)
from docmind_api.domain.auth.actors import AuthProvider, Role
from docmind_api.domain.auth.identity import IdentityLink, RoleAssignment
from docmind_api.domain.auth.users import DocMindUser, UserStatus


@dataclass(frozen=True, slots=True)
class EntraIdentityOnboardingCommand:
    """Input for binding a validated Entra identity to DocMind user state."""

    identity: MappedEntraIdentity


@dataclass(frozen=True, slots=True)
class EntraIdentityOnboardingResult:
    """Durable DocMind identity context for issuing a browser session."""

    user_id: UUID
    identity_link_id: UUID
    roles: frozenset[Role]
    created_user: bool


class EntraIdentityOnboardingUseCase:
    """Create or update DocMind identity state after a validated Entra login."""

    def __init__(
        self,
        *,
        users: DocMindUserRepository,
        identity_links: IdentityLinkRepository,
        role_assignments: RoleAssignmentRepository,
        clock: Clock,
        user_id_generator: DocMindUserIdGenerator,
        identity_link_id_generator: IdentityLinkIdGenerator,
    ) -> None:
        self._users = users
        self._identity_links = identity_links
        self._role_assignments = role_assignments
        self._clock = clock
        self._user_id_generator = user_id_generator
        self._identity_link_id_generator = identity_link_id_generator

    async def execute(
        self,
        command: EntraIdentityOnboardingCommand,
    ) -> EntraIdentityOnboardingResult | None:
        """Bind a mapped Entra identity to DocMind user state.

        A missing role mapping is an explicit deny: the use case does not return
        session-issuable identity context. For existing links, Entra-sourced role assignments
        are still refreshed to the empty provider snapshot.
        """

        identity = command.identity
        existing_link = await self._identity_links.get_by_provider_identity(
            provider=AuthProvider.ENTRA_ID,
            issuer=identity.issuer,
            tenant_id=identity.tenant_id,
            subject=identity.subject,
        )
        if existing_link is not None:
            await self._replace_role_assignments(
                user_id=existing_link.user_id,
                identity_link_id=existing_link.id,
                roles=identity.roles,
            )
            if not identity.roles:
                return None

            return EntraIdentityOnboardingResult(
                user_id=existing_link.user_id,
                identity_link_id=existing_link.id,
                roles=identity.roles,
                created_user=False,
            )

        if not identity.roles:
            return None

        timestamp = self._clock.now()
        user = DocMindUser(
            id=self._user_id_generator.new_id(),
            display_name=identity.display_name.strip(),
            status=UserStatus.ACTIVE,
            created_at=timestamp,
            updated_at=timestamp,
        )
        identity_link = IdentityLink(
            id=self._identity_link_id_generator.new_id(),
            user_id=user.id,
            provider=AuthProvider.ENTRA_ID,
            issuer=identity.issuer,
            tenant_id=identity.tenant_id,
            subject=identity.subject,
            email=identity.email,
            created_at=timestamp,
            updated_at=timestamp,
        )

        await self._users.add(user)
        await self._identity_links.add(identity_link)
        await self._replace_role_assignments(
            user_id=user.id,
            identity_link_id=identity_link.id,
            roles=identity.roles,
        )

        return EntraIdentityOnboardingResult(
            user_id=user.id,
            identity_link_id=identity_link.id,
            roles=identity.roles,
            created_user=True,
        )

    async def _replace_role_assignments(
        self,
        *,
        user_id: UUID,
        identity_link_id: UUID,
        roles: frozenset[Role],
    ) -> None:
        timestamp = self._clock.now()
        await self._role_assignments.replace_for_identity_link(
            user_id=user_id,
            identity_link_id=identity_link_id,
            role_assignments=tuple(
                _role_assignment(
                    user_id=user_id,
                    identity_link_id=identity_link_id,
                    role=role,
                    timestamp=timestamp,
                )
                for role in sorted(
                    roles,
                    key=lambda role: role.value,
                )
            ),
        )


def _role_assignment(
    *,
    user_id: UUID,
    identity_link_id: UUID,
    role: Role,
    timestamp: datetime,
) -> RoleAssignment:
    return RoleAssignment(
        user_id=user_id,
        role=role,
        source_provider=AuthProvider.ENTRA_ID,
        identity_link_id=identity_link_id,
        created_at=timestamp,
        updated_at=timestamp,
    )
