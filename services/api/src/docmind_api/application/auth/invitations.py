"""Application use cases for admin-managed user invitations."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from docmind_api.application.auth.ports import (
    Clock,
    InvitationTokenGenerator,
    InvitationTokenHasher,
    UserInvitationRepository,
)
from docmind_api.application.listing import (
    ListPage,
    ListRequest,
    ListSortDirection,
    filter_bounded_list,
    process_bounded_list,
)
from docmind_api.domain.auth.actors import AuthenticatedActor, Role
from docmind_api.domain.auth.invitations import (
    InvitationStatus,
    UserInvitation,
    normalize_invitation_email,
    normalize_invitation_roles,
)
from docmind_backend_runtime.errors import ApplicationError


@dataclass(frozen=True, slots=True)
class CreateUserInvitationCommand:
    """Input for creating a pending user invitation."""

    email: str
    roles: tuple[Role, ...]
    actor: AuthenticatedActor


@dataclass(frozen=True, slots=True)
class ListUserInvitationsCommand:
    """Input for listing user invitations."""

    actor: AuthenticatedActor


class UserInvitationListStatus(StrEnum):
    """Lifecycle filters supported by the invitation list."""

    PENDING = InvitationStatus.PENDING.value
    CANCELLED = InvitationStatus.CANCELLED.value
    ACCEPTED = InvitationStatus.ACCEPTED.value
    ALL = "all"


class UserInvitationSortField(StrEnum):
    """Safe sort keys exposed by the invitation list."""

    EMAIL = "email"
    ROLES = "roles"
    STATUS = "status"
    EXPIRES_AT = "expires_at"
    CREATED_AT = "created_at"


@dataclass(frozen=True, slots=True)
class ListUserInvitationsPageCommand:
    """Input for a searched, faceted, and paged invitation list."""

    actor: AuthenticatedActor
    status: UserInvitationListStatus = UserInvitationListStatus.ALL
    search: str | None = None
    sort_by: UserInvitationSortField = UserInvitationSortField.CREATED_AT
    sort_direction: ListSortDirection = ListSortDirection.ASC
    limit: int = 50
    offset: int = 0


@dataclass(frozen=True, slots=True)
class CancelUserInvitationCommand:
    """Input for cancelling a pending user invitation."""

    invitation_id: UUID
    actor: AuthenticatedActor


@dataclass(frozen=True, slots=True)
class UserInvitationResult:
    """Application result for a single invitation."""

    invitation: UserInvitation
    delivery_available: bool
    evaluated_at: datetime


@dataclass(frozen=True, slots=True)
class UserInvitationListResult:
    """Application result for an invitation list."""

    invitations: tuple[UserInvitation, ...]
    delivery_available: bool
    evaluated_at: datetime


@dataclass(frozen=True, slots=True)
class UserInvitationPageResult:
    """Paged invitations plus lifecycle facets."""

    page: ListPage[UserInvitation]
    delivery_available: bool
    evaluated_at: datetime
    pending_count: int
    cancelled_count: int
    accepted_count: int
    status: UserInvitationListStatus


class PendingInvitationAlreadyExistsError(ApplicationError):
    """Raised when an email already has a pending invitation."""

    def __init__(self) -> None:
        super().__init__(
            code="PENDING_INVITATION_EXISTS",
            message="A pending invitation already exists for this email.",
            status_code=409,
        )


class UserInvitationNotFoundError(ApplicationError):
    """Raised when an invitation does not exist or cannot be changed."""

    def __init__(self) -> None:
        super().__init__(
            code="INVITATION_NOT_FOUND",
            message="Invitation was not found.",
            status_code=404,
        )


class InvalidUserInvitationError(ApplicationError):
    """Raised when an invitation command is invalid."""

    def __init__(self) -> None:
        super().__init__(
            code="INVALID_INVITATION",
            message="Invitation request is invalid.",
            status_code=422,
        )


class UserInvitationIdGenerator(Protocol):
    """Structural type for UUID generators used by invitation use cases."""

    def new_id(self) -> UUID: ...


class UserInvitationService:
    """Orchestrates admin-owned invitation lifecycle operations."""

    def __init__(
        self,
        *,
        repository: UserInvitationRepository,
        token_generator: InvitationTokenGenerator,
        token_hasher: InvitationTokenHasher,
        clock: Clock,
        id_generator: UserInvitationIdGenerator,
        invitation_lifetime: timedelta,
        delivery_available: bool = False,
    ) -> None:
        self._repository = repository
        self._token_generator = token_generator
        self._token_hasher = token_hasher
        self._clock = clock
        self._id_generator = id_generator
        self._invitation_lifetime = invitation_lifetime
        self._delivery_available = delivery_available

    async def create_invitation(
        self,
        command: CreateUserInvitationCommand,
    ) -> UserInvitationResult:
        """Create a pending invitation for a normalized email and role set."""

        now = self._clock.now()
        try:
            email = normalize_invitation_email(command.email)
            roles = normalize_invitation_roles(command.roles)
        except ValueError as error:
            raise InvalidUserInvitationError() from error
        email_slot_available = await self._repository.acquire_pending_email_creation_slot(
            email=email,
            evaluated_at=now,
        )
        if not email_slot_available:
            raise PendingInvitationAlreadyExistsError()

        raw_token = self._token_generator.new_token()
        invitation = UserInvitation(
            id=self._id_generator.new_id(),
            email=email,
            roles=roles,
            token_hash=self._token_hasher.hash_token(raw_token),
            status=InvitationStatus.PENDING,
            created_by_user_id=UUID(command.actor.actor_id),
            created_at=now,
            updated_at=now,
            expires_at=now + self._invitation_lifetime,
        )
        await self._repository.add(invitation)
        return UserInvitationResult(
            invitation=invitation,
            delivery_available=self._delivery_available,
            evaluated_at=now,
        )

    async def list_invitations(
        self,
        _command: ListUserInvitationsCommand,
    ) -> UserInvitationListResult:
        """List active pending and completed invitations newest first."""

        now = self._clock.now()
        return UserInvitationListResult(
            invitations=await self._repository.list_all(evaluated_at=now),
            delivery_available=self._delivery_available,
            evaluated_at=now,
        )

    async def list_invitation_page(
        self,
        command: ListUserInvitationsPageCommand,
    ) -> UserInvitationPageResult:
        """Search, facet, sort, and page invitations inside the application boundary."""

        now = self._clock.now()
        invitations = await self._repository.list_all(evaluated_at=now)
        matching_invitations = filter_bounded_list(
            invitations,
            search=command.search,
            search_values=lambda invitation: (
                invitation.email,
                invitation.status.value,
                *(role.value for role in invitation.roles),
            ),
        )
        pending_count = sum(
            invitation.status is InvitationStatus.PENDING for invitation in matching_invitations
        )
        cancelled_count = sum(
            invitation.status is InvitationStatus.CANCELLED for invitation in matching_invitations
        )
        status_filtered = tuple(
            invitation
            for invitation in matching_invitations
            if command.status is UserInvitationListStatus.ALL
            or invitation.status.value == command.status.value
        )
        page = process_bounded_list(
            status_filtered,
            request=ListRequest(
                search=None,
                sort_by=command.sort_by,
                sort_direction=command.sort_direction,
                limit=command.limit,
                offset=command.offset,
            ),
            search_values=lambda _invitation: (),
            sort_value=_invitation_sort_value,
            identity=lambda invitation: invitation.id,
        )
        return UserInvitationPageResult(
            page=page,
            delivery_available=self._delivery_available,
            evaluated_at=now,
            pending_count=pending_count,
            cancelled_count=cancelled_count,
            accepted_count=len(matching_invitations) - pending_count - cancelled_count,
            status=command.status,
        )

    async def cancel_invitation(
        self,
        command: CancelUserInvitationCommand,
    ) -> UserInvitationResult:
        """Cancel a pending invitation."""

        now = self._clock.now()
        invitation = await self._repository.cancel(
            invitation_id=command.invitation_id,
            cancelled_at=now,
            cancelled_by_user_id=UUID(command.actor.actor_id),
        )
        if invitation is None:
            raise UserInvitationNotFoundError()

        return UserInvitationResult(
            invitation=invitation,
            delivery_available=self._delivery_available,
            evaluated_at=now,
        )


def _invitation_sort_value(
    invitation: UserInvitation,
    sort_by: UserInvitationSortField,
) -> str | datetime:
    if sort_by is UserInvitationSortField.EMAIL:
        return invitation.email
    if sort_by is UserInvitationSortField.ROLES:
        return " ".join(role.value for role in invitation.roles)
    if sort_by is UserInvitationSortField.STATUS:
        return invitation.status.value
    if sort_by is UserInvitationSortField.EXPIRES_AT:
        return invitation.expires_at
    return invitation.created_at
