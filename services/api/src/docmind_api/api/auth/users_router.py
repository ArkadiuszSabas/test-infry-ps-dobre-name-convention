"""HTTP user-management endpoints."""

from collections.abc import Awaitable, Callable
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response

from docmind_api.api.auth.dependencies import (
    DOCMIND_REFRESH_COOKIE,
    DOCMIND_SESSION_COOKIE,
    require_authenticated,
)
from docmind_api.api.auth.schemas import (
    ChangeOwnPasswordEnvelope,
    ChangeOwnPasswordRequest,
    ChangeOwnPasswordSchema,
    CreateManagedLocalUserRequest,
    DeleteManagedUserEnvelope,
    DeleteManagedUserSchema,
    ManagedUserEnvelope,
    ManagedUserListEnvelope,
    ManagedUserListMetaSchema,
    ManagedUserListSchema,
    ManagedUserOperationMetaSchema,
    ManagedUserSchema,
    SetManagedUserPasswordEnvelope,
    SetManagedUserPasswordRequest,
    SetManagedUserPasswordSchema,
    UpdateManagedUserRequest,
)
from docmind_api.application.auth.passwords import (
    ChangeOwnPasswordCommand,
    ChangeOwnPasswordResult,
    OwnPasswordService,
)
from docmind_api.application.auth.users import (
    CreateManagedLocalUserCommand,
    DeleteUserCommand,
    DeleteUserResult,
    GetUserCommand,
    ListUsersCommand,
    ManagedUserListResult,
    ManagedUserResult,
    SetUserPasswordCommand,
    SetUserPasswordResult,
    UpdateUserCommand,
    UserAdministrationService,
)
from docmind_api.domain.auth.actors import AuthenticatedActor
from docmind_api.domain.auth.users import ManagedUser, UserStatus

UserAdministrationServiceDependency = Callable[..., UserAdministrationService]
OwnPasswordServiceDependency = Callable[..., OwnPasswordService]
AuthenticatedActorDependency = Callable[..., Awaitable[AuthenticatedActor]]
CookieCsrfProtectionDependency = Callable[..., Awaitable[None]]


def register_user_management_routes(
    router: APIRouter,
    *,
    user_administration_service_dependency: UserAdministrationServiceDependency,
    own_password_service_dependency: OwnPasswordServiceDependency,
    require_admin_users_manage: AuthenticatedActorDependency,
    cookie_csrf_protection: CookieCsrfProtectionDependency,
) -> None:
    """Register admin user-management and self-service password routes."""

    async def list_users(
        admin_actor: Annotated[AuthenticatedActor, Depends(require_admin_users_manage)],
        user_administration: Annotated[
            UserAdministrationService,
            Depends(user_administration_service_dependency),
        ],
        include_deleted: Annotated[
            bool,
            Query(description="Include soft-deleted users in the response."),
        ] = False,
    ) -> ManagedUserListEnvelope:
        result = await user_administration.list_users(
            ListUsersCommand(actor=admin_actor, include_deleted=include_deleted),
        )
        return _to_managed_user_list_envelope(
            result,
            include_deleted=include_deleted,
        )

    async def create_user(
        request: CreateManagedLocalUserRequest,
        admin_actor: Annotated[AuthenticatedActor, Depends(require_admin_users_manage)],
        user_administration: Annotated[
            UserAdministrationService,
            Depends(user_administration_service_dependency),
        ],
    ) -> ManagedUserEnvelope:
        result = await user_administration.create_local_user(
            CreateManagedLocalUserCommand(
                login=request.login,
                display_name=request.display_name,
                plaintext_password=request.password,
                roles=tuple(request.roles),
                status=UserStatus(request.status.value),
                actor=admin_actor,
            ),
        )
        return _to_managed_user_envelope(result)

    async def get_user(
        user_id: UUID,
        admin_actor: Annotated[AuthenticatedActor, Depends(require_admin_users_manage)],
        user_administration: Annotated[
            UserAdministrationService,
            Depends(user_administration_service_dependency),
        ],
    ) -> ManagedUserEnvelope:
        result = await user_administration.get_user(
            GetUserCommand(user_id=user_id, actor=admin_actor),
        )
        return _to_managed_user_envelope(result)

    async def update_user(
        user_id: UUID,
        request: UpdateManagedUserRequest,
        admin_actor: Annotated[AuthenticatedActor, Depends(require_admin_users_manage)],
        user_administration: Annotated[
            UserAdministrationService,
            Depends(user_administration_service_dependency),
        ],
    ) -> ManagedUserEnvelope:
        result = await user_administration.update_user(
            UpdateUserCommand(
                user_id=user_id,
                actor=admin_actor,
                display_name=request.display_name,
                roles=tuple(request.roles) if request.roles is not None else None,
                status=UserStatus(request.status.value) if request.status is not None else None,
            ),
        )
        return _to_managed_user_envelope(result)

    async def delete_user(
        user_id: UUID,
        admin_actor: Annotated[AuthenticatedActor, Depends(require_admin_users_manage)],
        user_administration: Annotated[
            UserAdministrationService,
            Depends(user_administration_service_dependency),
        ],
    ) -> DeleteManagedUserEnvelope:
        result = await user_administration.delete_user(
            DeleteUserCommand(user_id=user_id, actor=admin_actor),
        )
        return _to_delete_managed_user_envelope(result)

    async def set_user_password(
        user_id: UUID,
        request: SetManagedUserPasswordRequest,
        admin_actor: Annotated[AuthenticatedActor, Depends(require_admin_users_manage)],
        user_administration: Annotated[
            UserAdministrationService,
            Depends(user_administration_service_dependency),
        ],
    ) -> SetManagedUserPasswordEnvelope:
        result = await user_administration.set_user_password(
            SetUserPasswordCommand(
                user_id=user_id,
                actor=admin_actor,
                new_password=request.new_password,
            ),
        )
        return _to_set_managed_user_password_envelope(result)

    async def change_own_password(
        request: ChangeOwnPasswordRequest,
        response: Response,
        actor: Annotated[AuthenticatedActor, Depends(require_authenticated)],
        own_password_service: Annotated[
            OwnPasswordService,
            Depends(own_password_service_dependency),
        ],
    ) -> ChangeOwnPasswordEnvelope:
        result = await own_password_service.change_own_password(
            ChangeOwnPasswordCommand(
                actor=actor,
                current_password=request.current_password,
                new_password=request.new_password,
            ),
        )
        _clear_auth_cookies(response)
        return _to_change_own_password_envelope(result)

    router.add_api_route(
        "/users",
        list_users,
        methods=["GET"],
        response_model=ManagedUserListEnvelope,
    )
    router.add_api_route(
        "/users",
        create_user,
        methods=["POST"],
        status_code=201,
        response_model=ManagedUserEnvelope,
        dependencies=[Depends(cookie_csrf_protection)],
    )
    router.add_api_route(
        "/users/{user_id}",
        get_user,
        methods=["GET"],
        response_model=ManagedUserEnvelope,
    )
    router.add_api_route(
        "/users/{user_id}",
        update_user,
        methods=["PATCH"],
        response_model=ManagedUserEnvelope,
        dependencies=[Depends(cookie_csrf_protection)],
    )
    router.add_api_route(
        "/users/{user_id}",
        delete_user,
        methods=["DELETE"],
        response_model=DeleteManagedUserEnvelope,
        dependencies=[Depends(cookie_csrf_protection)],
    )
    router.add_api_route(
        "/users/{user_id}/password",
        set_user_password,
        methods=["PUT"],
        response_model=SetManagedUserPasswordEnvelope,
        dependencies=[Depends(cookie_csrf_protection)],
    )
    router.add_api_route(
        "/me/password",
        change_own_password,
        methods=["PUT"],
        response_model=ChangeOwnPasswordEnvelope,
        dependencies=[Depends(cookie_csrf_protection)],
    )


def _to_managed_user_envelope(result: ManagedUserResult) -> ManagedUserEnvelope:
    return ManagedUserEnvelope(
        data=_to_managed_user_schema(result.user),
        meta=ManagedUserOperationMetaSchema(
            evaluated_at=result.evaluated_at,
            revoked_sessions=result.revoked_sessions,
        ),
    )


def _to_managed_user_list_envelope(
    result: ManagedUserListResult,
    *,
    include_deleted: bool,
) -> ManagedUserListEnvelope:
    return ManagedUserListEnvelope(
        data=ManagedUserListSchema(
            users=[_to_managed_user_schema(user) for user in result.users],
        ),
        meta=ManagedUserListMetaSchema(
            evaluated_at=result.evaluated_at,
            total_count=result.total_count,
            returned_count=result.returned_count,
            include_deleted=include_deleted,
        ),
    )


def _to_delete_managed_user_envelope(
    result: DeleteUserResult,
) -> DeleteManagedUserEnvelope:
    return DeleteManagedUserEnvelope(
        data=DeleteManagedUserSchema(id=result.user_id, deleted=result.deleted),
        meta=ManagedUserOperationMetaSchema(
            evaluated_at=result.evaluated_at,
            revoked_sessions=result.revoked_sessions,
        ),
    )


def _to_set_managed_user_password_envelope(
    result: SetUserPasswordResult,
) -> SetManagedUserPasswordEnvelope:
    return SetManagedUserPasswordEnvelope(
        data=SetManagedUserPasswordSchema(id=result.user_id, changed=result.changed),
        meta=ManagedUserOperationMetaSchema(
            evaluated_at=result.evaluated_at,
            revoked_sessions=result.revoked_sessions,
        ),
    )


def _to_change_own_password_envelope(
    result: ChangeOwnPasswordResult,
) -> ChangeOwnPasswordEnvelope:
    return ChangeOwnPasswordEnvelope(
        data=ChangeOwnPasswordSchema(changed=result.changed),
        meta=ManagedUserOperationMetaSchema(
            evaluated_at=result.evaluated_at,
            revoked_sessions=result.revoked_sessions,
        ),
    )


def _to_managed_user_schema(user: ManagedUser) -> ManagedUserSchema:
    return ManagedUserSchema(
        id=user.id,
        display_name=user.display_name,
        status=user.status,
        roles=list(user.roles),
        auth_providers=list(user.auth_providers),
        email=user.email,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


def _clear_auth_cookies(response: Response) -> None:
    for cookie_name in (DOCMIND_SESSION_COOKIE, DOCMIND_REFRESH_COOKIE):
        response.delete_cookie(
            key=cookie_name,
            path="/",
            secure=True,
            httponly=True,
            samesite="lax",
        )
