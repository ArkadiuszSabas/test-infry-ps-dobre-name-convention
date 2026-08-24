"""HTTP invitation endpoints for admin user onboarding."""

from collections.abc import Awaitable, Callable
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from docmind_api.api.auth.schemas import (
    UserInvitationCreateRequest,
    UserInvitationEnvelope,
    UserInvitationListEnvelope,
    UserInvitationListSchema,
    UserInvitationSchema,
)
from docmind_api.application.auth.invitations import (
    CancelUserInvitationCommand,
    CreateUserInvitationCommand,
    ListPendingUserInvitationsCommand,
    UserInvitationListResult,
    UserInvitationResult,
    UserInvitationService,
)
from docmind_api.domain.auth.actors import AuthenticatedActor
from docmind_api.domain.auth.invitations import UserInvitation

UserInvitationServiceDependency = Callable[..., UserInvitationService]
AuthenticatedActorDependency = Callable[..., Awaitable[AuthenticatedActor]]
CookieCsrfProtectionDependency = Callable[..., Awaitable[None]]


def register_invitation_routes(
    router: APIRouter,
    *,
    user_invitation_service_dependency: UserInvitationServiceDependency,
    require_admin_users_manage: AuthenticatedActorDependency,
    cookie_csrf_protection: CookieCsrfProtectionDependency,
) -> None:
    """Register admin invitation routes on the auth router."""

    async def list_pending_invitations(
        admin_actor: Annotated[AuthenticatedActor, Depends(require_admin_users_manage)],
        invitation_service: Annotated[
            UserInvitationService,
            Depends(user_invitation_service_dependency),
        ],
    ) -> UserInvitationListEnvelope:
        result = await invitation_service.list_pending_invitations(
            ListPendingUserInvitationsCommand(actor=admin_actor),
        )
        return _to_user_invitation_list_envelope(result)

    async def create_invitation(
        request: UserInvitationCreateRequest,
        admin_actor: Annotated[AuthenticatedActor, Depends(require_admin_users_manage)],
        invitation_service: Annotated[
            UserInvitationService,
            Depends(user_invitation_service_dependency),
        ],
    ) -> UserInvitationEnvelope:
        result = await invitation_service.create_invitation(
            CreateUserInvitationCommand(
                email=request.email,
                roles=tuple(request.roles),
                actor=admin_actor,
            ),
        )
        return _to_user_invitation_envelope(result)

    async def cancel_invitation(
        invitation_id: UUID,
        admin_actor: Annotated[AuthenticatedActor, Depends(require_admin_users_manage)],
        invitation_service: Annotated[
            UserInvitationService,
            Depends(user_invitation_service_dependency),
        ],
    ) -> UserInvitationEnvelope:
        result = await invitation_service.cancel_invitation(
            CancelUserInvitationCommand(
                invitation_id=invitation_id,
                actor=admin_actor,
            ),
        )
        return _to_user_invitation_envelope(result)

    router.add_api_route(
        "/invitations",
        list_pending_invitations,
        methods=["GET"],
        response_model=UserInvitationListEnvelope,
    )
    router.add_api_route(
        "/invitations",
        create_invitation,
        methods=["POST"],
        response_model=UserInvitationEnvelope,
        status_code=201,
        dependencies=[Depends(cookie_csrf_protection)],
    )
    router.add_api_route(
        "/invitations/{invitation_id}/cancel",
        cancel_invitation,
        methods=["POST"],
        response_model=UserInvitationEnvelope,
        dependencies=[Depends(cookie_csrf_protection)],
    )


def _to_user_invitation_envelope(
    result: UserInvitationResult,
) -> UserInvitationEnvelope:
    return UserInvitationEnvelope(
        data=_to_user_invitation_schema(result.invitation),
        meta={
            "delivery_available": result.delivery_available,
            "evaluated_at": result.evaluated_at,
        },
    )


def _to_user_invitation_list_envelope(
    result: UserInvitationListResult,
) -> UserInvitationListEnvelope:
    return UserInvitationListEnvelope(
        data=UserInvitationListSchema(
            invitations=[
                _to_user_invitation_schema(invitation) for invitation in result.invitations
            ],
        ),
        meta={
            "delivery_available": result.delivery_available,
            "evaluated_at": result.evaluated_at,
        },
    )


def _to_user_invitation_schema(invitation: UserInvitation) -> UserInvitationSchema:
    return UserInvitationSchema(
        id=invitation.id,
        email=invitation.email,
        roles=list(invitation.roles),
        status=invitation.status,
        created_by_user_id=invitation.created_by_user_id,
        created_at=invitation.created_at,
        updated_at=invitation.updated_at,
        expires_at=invitation.expires_at,
        cancelled_at=invitation.cancelled_at,
        cancelled_by_user_id=invitation.cancelled_by_user_id,
        accepted_at=invitation.accepted_at,
        accepted_by_user_id=invitation.accepted_by_user_id,
    )
