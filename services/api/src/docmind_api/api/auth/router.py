"""HTTP auth endpoints for the DocMind.ai API service."""

from collections.abc import Callable
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Cookie, Depends, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse

from docmind_api.api.auth.dependencies import (
    CSRF_HEADER,
    DOCMIND_REFRESH_COOKIE,
    DOCMIND_SESSION_COOKIE,
    AuthenticationRequiredError,
    require_authenticated,
    require_cookie_csrf_protection,
    require_permissions,
)
from docmind_api.api.auth.invitations_router import register_invitation_routes
from docmind_api.api.auth.schemas import (
    BrowserSessionSchema,
    CsrfTokenEnvelope,
    CsrfTokenSchema,
    CurrentActorEnvelope,
    CurrentActorSchema,
    LocalLoginEnvelope,
    LocalLoginRequest,
    LocalLoginSchema,
    LogoutEnvelope,
    LogoutSchema,
    RefreshSessionEnvelope,
    RefreshSessionSchema,
    UserSessionListEnvelope,
    UserSessionRevocationEnvelope,
)
from docmind_api.api.auth.session_mappers import (
    to_session_list_envelope,
    to_session_revocation_envelope,
)
from docmind_api.api.auth.session_metadata import session_client_metadata
from docmind_api.api.auth.users_router import register_user_management_routes
from docmind_api.application.auth.entra_oidc import (
    CompleteEntraOidcLoginCommand,
    CompleteEntraOidcLoginUseCase,
    EntraOidcCallbackFailureReason,
    EntraOidcCallbackRejectedError,
    StartEntraOidcLoginCommand,
    StartEntraOidcLoginUseCase,
)
from docmind_api.application.auth.invitations import UserInvitationService
from docmind_api.application.auth.local_accounts import (
    LocalLoginCommand,
    LocalLoginUseCase,
)
from docmind_api.application.auth.passwords import OwnPasswordService
from docmind_api.application.auth.ports import OpaqueRefreshToken, OpaqueSessionToken
from docmind_api.application.auth.session_management import (
    ListOwnUserSessionsCommand,
    ListUserSessionsCommand,
    RevokeOwnUserSessionCommand,
    RevokeUserSessionForUserCommand,
    UserSessionManagementService,
)
from docmind_api.application.auth.sessions import (
    InvalidRefreshTokenError,
    IssueCsrfTokenCommand,
    RefreshBrowserSessionCommand,
    RevokeRefreshTokenFamilyCommand,
    RevokeUserSessionCommand,
    UserSessionService,
)
from docmind_api.application.auth.users import UserAdministrationService
from docmind_api.domain.auth.actors import AuthenticatedActor, Permission
from docmind_api.domain.auth.sessions import SessionRefreshToken, UserSession

ENTRA_OIDC_BROWSER_BINDING_COOKIE = "__Host-docmind_entra_oidc"
LocalLoginUseCaseDependency = Callable[..., LocalLoginUseCase]
UserSessionServiceDependency = Callable[..., UserSessionService]
UserSessionManagementServiceDependency = Callable[..., UserSessionManagementService]
UserInvitationServiceDependency = Callable[..., UserInvitationService]
UserAdministrationServiceDependency = Callable[..., UserAdministrationService]
OwnPasswordServiceDependency = Callable[..., OwnPasswordService]
StartEntraOidcLoginUseCaseDependency = Callable[..., StartEntraOidcLoginUseCase]
CompleteEntraOidcLoginUseCaseDependency = Callable[..., CompleteEntraOidcLoginUseCase]


def create_auth_router(
    *,
    local_login_use_case_dependency: LocalLoginUseCaseDependency,
    user_session_service_dependency: UserSessionServiceDependency,
    user_session_management_service_dependency: UserSessionManagementServiceDependency,
    user_invitation_service_dependency: UserInvitationServiceDependency,
    user_administration_service_dependency: UserAdministrationServiceDependency,
    own_password_service_dependency: OwnPasswordServiceDependency,
    start_entra_oidc_login_use_case_dependency: StartEntraOidcLoginUseCaseDependency,
    complete_entra_oidc_login_use_case_dependency: CompleteEntraOidcLoginUseCaseDependency,
    allowed_browser_origins: tuple[str, ...],
    entra_oidc_enabled: bool,
) -> APIRouter:
    """Create the auth router."""

    router = APIRouter(prefix="/auth", tags=["auth"])
    cookie_csrf_protection = require_cookie_csrf_protection(
        allowed_browser_origins,
        user_session_service_dependency,
    )
    require_admin_users_manage = require_permissions(Permission.ADMIN_USERS_MANAGE)

    async def login_local(
        http_request: Request,
        login_request: LocalLoginRequest,
        response: Response,
        local_login_use_case: Annotated[
            LocalLoginUseCase,
            Depends(local_login_use_case_dependency),
        ],
    ) -> LocalLoginEnvelope:
        login_result = await local_login_use_case.execute(
            LocalLoginCommand(
                login=login_request.login,
                plaintext_password=login_request.password,
                client_metadata=session_client_metadata(http_request),
            ),
        )
        _set_session_cookie(
            response,
            session=login_result.session,
            token=login_result.token,
        )
        _set_refresh_cookie(
            response,
            refresh_token_record=login_result.refresh_token_record,
            token=login_result.refresh_token,
        )

        return LocalLoginEnvelope(
            data=LocalLoginSchema(
                user=_to_current_actor_schema(login_result.actor),
                session=BrowserSessionSchema(expires_at=login_result.session.expires_at),
                csrf=_to_csrf_token_schema(login_result.csrf_token.value),
            ),
        )

    async def get_csrf_token(
        user_session_service: Annotated[
            UserSessionService,
            Depends(user_session_service_dependency),
        ],
        session_token: Annotated[
            str | None,
            Cookie(alias=DOCMIND_SESSION_COOKIE),
        ] = None,
    ) -> CsrfTokenEnvelope:
        if session_token is None or not session_token.strip():
            raise AuthenticationRequiredError()

        issued_token = await user_session_service.issue_csrf_token(
            IssueCsrfTokenCommand(token=OpaqueSessionToken(session_token.strip())),
        )
        if issued_token is None:
            raise AuthenticationRequiredError()

        return CsrfTokenEnvelope(
            data=_to_csrf_token_schema(issued_token.token.value),
        )

    async def logout(
        response: Response,
        user_session_service: Annotated[
            UserSessionService,
            Depends(user_session_service_dependency),
        ],
        session_token: Annotated[
            str | None,
            Cookie(alias=DOCMIND_SESSION_COOKIE),
        ] = None,
        refresh_token: Annotated[
            str | None,
            Cookie(alias=DOCMIND_REFRESH_COOKIE),
        ] = None,
    ) -> LogoutEnvelope:
        revoked = False
        if refresh_token is not None and refresh_token.strip():
            revoke_refresh_result = await user_session_service.revoke_refresh_token_family(
                RevokeRefreshTokenFamilyCommand(
                    token=OpaqueRefreshToken(refresh_token),
                ),
            )
            revoked = revoke_refresh_result.revoked

        if session_token is not None and session_token.strip():
            revoke_result = await user_session_service.revoke_session(
                RevokeUserSessionCommand(
                    token=OpaqueSessionToken(session_token),
                ),
            )
            revoked = revoked or revoke_result.revoked

        _clear_session_cookie(response)
        _clear_refresh_cookie(response)
        return LogoutEnvelope(data=LogoutSchema(revoked=revoked))

    async def refresh_session(
        response: Response,
        user_session_service: Annotated[
            UserSessionService,
            Depends(user_session_service_dependency),
        ],
        refresh_token: Annotated[
            str | None,
            Cookie(alias=DOCMIND_REFRESH_COOKIE),
        ] = None,
    ) -> RefreshSessionEnvelope | JSONResponse:
        if refresh_token is None or not refresh_token.strip():
            return _invalid_refresh_token_response()

        try:
            refresh_result = await user_session_service.refresh_session(
                RefreshBrowserSessionCommand(token=OpaqueRefreshToken(refresh_token)),
            )
        except InvalidRefreshTokenError:
            return _invalid_refresh_token_response()

        _set_session_cookie(
            response,
            session=refresh_result.session,
            token=refresh_result.token,
        )
        _set_refresh_cookie(
            response,
            refresh_token_record=refresh_result.refresh_token_record,
            token=refresh_result.refresh_token,
        )

        return RefreshSessionEnvelope(
            data=RefreshSessionSchema(
                user=_to_current_actor_schema(refresh_result.actor),
                session=BrowserSessionSchema(expires_at=refresh_result.session.expires_at),
            ),
        )

    async def get_current_actor(
        actor: Annotated[AuthenticatedActor, Depends(require_authenticated)],
    ) -> CurrentActorEnvelope:
        return _to_current_actor_envelope(actor)

    async def list_own_sessions(
        actor: Annotated[AuthenticatedActor, Depends(require_authenticated)],
        session_management: Annotated[
            UserSessionManagementService,
            Depends(user_session_management_service_dependency),
        ],
    ) -> UserSessionListEnvelope:
        result = await session_management.list_own_sessions(
            ListOwnUserSessionsCommand(actor=actor),
        )
        return to_session_list_envelope(result)

    async def revoke_own_session(
        session_id: UUID,
        actor: Annotated[AuthenticatedActor, Depends(require_authenticated)],
        session_management: Annotated[
            UserSessionManagementService,
            Depends(user_session_management_service_dependency),
        ],
    ) -> UserSessionRevocationEnvelope:
        result = await session_management.revoke_own_session(
            RevokeOwnUserSessionCommand(actor=actor, session_id=session_id),
        )
        return to_session_revocation_envelope(result)

    async def list_user_sessions(
        user_id: UUID,
        _admin_actor: Annotated[AuthenticatedActor, Depends(require_admin_users_manage)],
        session_management: Annotated[
            UserSessionManagementService,
            Depends(user_session_management_service_dependency),
        ],
    ) -> UserSessionListEnvelope:
        result = await session_management.list_user_sessions(
            ListUserSessionsCommand(user_id=user_id),
        )
        return to_session_list_envelope(result)

    async def revoke_user_session(
        user_id: UUID,
        session_id: UUID,
        admin_actor: Annotated[AuthenticatedActor, Depends(require_admin_users_manage)],
        session_management: Annotated[
            UserSessionManagementService,
            Depends(user_session_management_service_dependency),
        ],
    ) -> UserSessionRevocationEnvelope:
        result = await session_management.revoke_user_session(
            RevokeUserSessionForUserCommand(user_id=user_id, session_id=session_id),
            actor=admin_actor,
        )
        return to_session_revocation_envelope(result)

    async def start_entra_login(
        redirect_target: str,
        start_login_use_case: Annotated[
            StartEntraOidcLoginUseCase,
            Depends(start_entra_oidc_login_use_case_dependency),
        ],
    ) -> RedirectResponse:
        result = await start_login_use_case.execute(
            StartEntraOidcLoginCommand(redirect_target=redirect_target),
        )
        redirect_response = RedirectResponse(
            url=result.authorization_url,
            status_code=302,
        )
        _set_entra_oidc_browser_binding_cookie(
            redirect_response,
            browser_binding=result.browser_binding,
            max_age=int(result.transaction_ttl.total_seconds()),
        )
        return redirect_response

    async def complete_entra_login(
        complete_login_use_case: Annotated[
            CompleteEntraOidcLoginUseCase,
            Depends(complete_entra_oidc_login_use_case_dependency),
        ],
        code: str | None = None,
        state: str | None = None,
        error: str | None = None,
        browser_binding: Annotated[
            str | None,
            Cookie(alias=ENTRA_OIDC_BROWSER_BINDING_COOKIE),
        ] = None,
    ) -> Response:
        if error is not None:
            raise EntraOidcCallbackRejectedError(
                reason=EntraOidcCallbackFailureReason.PROVIDER_ERROR,
            )
        if code is None or state is None or not code.strip() or not state.strip():
            raise EntraOidcCallbackRejectedError(
                reason=EntraOidcCallbackFailureReason.MISSING_PARAMETERS,
            )
        if browser_binding is None or not browser_binding.strip():
            raise EntraOidcCallbackRejectedError(
                reason=EntraOidcCallbackFailureReason.INVALID_BROWSER_BINDING,
            )

        try:
            result = await complete_login_use_case.execute(
                CompleteEntraOidcLoginCommand(
                    code=code,
                    state=state,
                    browser_binding=browser_binding,
                ),
            )
        except EntraOidcCallbackRejectedError as rejected_error:
            if rejected_error.reason == EntraOidcCallbackFailureReason.UNMAPPED_IDENTITY:
                return _entra_oidc_callback_rejected_response(rejected_error)
            raise
        redirect_response = RedirectResponse(
            url=result.redirect_target,
            status_code=302,
        )
        _clear_entra_oidc_browser_binding_cookie(redirect_response)
        _set_session_cookie(
            redirect_response,
            session=result.session,
            token=result.token,
        )
        _set_refresh_cookie(
            redirect_response,
            refresh_token_record=result.refresh_token_record,
            token=result.refresh_token,
        )
        return redirect_response

    router.add_api_route(
        "/local/login",
        login_local,
        methods=["POST"],
        response_model=LocalLoginEnvelope,
        dependencies=[Depends(cookie_csrf_protection)],
    )
    router.add_api_route(
        "/logout",
        logout,
        methods=["POST"],
        response_model=LogoutEnvelope,
        dependencies=[Depends(cookie_csrf_protection)],
    )
    router.add_api_route(
        "/csrf",
        get_csrf_token,
        methods=["GET"],
        response_model=CsrfTokenEnvelope,
    )
    router.add_api_route(
        "/refresh",
        refresh_session,
        methods=["POST"],
        response_model=RefreshSessionEnvelope,
        dependencies=[Depends(cookie_csrf_protection)],
    )
    router.add_api_route(
        "/me",
        get_current_actor,
        methods=["GET"],
        response_model=CurrentActorEnvelope,
    )
    router.add_api_route(
        "/sessions",
        list_own_sessions,
        methods=["GET"],
        response_model=UserSessionListEnvelope,
    )
    router.add_api_route(
        "/sessions/{session_id}/revoke",
        revoke_own_session,
        methods=["POST"],
        response_model=UserSessionRevocationEnvelope,
        dependencies=[Depends(cookie_csrf_protection)],
    )
    router.add_api_route(
        "/users/{user_id}/sessions",
        list_user_sessions,
        methods=["GET"],
        response_model=UserSessionListEnvelope,
    )
    router.add_api_route(
        "/users/{user_id}/sessions/{session_id}/revoke",
        revoke_user_session,
        methods=["POST"],
        response_model=UserSessionRevocationEnvelope,
        dependencies=[Depends(cookie_csrf_protection)],
    )
    register_invitation_routes(
        router,
        user_invitation_service_dependency=user_invitation_service_dependency,
        require_admin_users_manage=require_admin_users_manage,
        cookie_csrf_protection=cookie_csrf_protection,
    )
    register_user_management_routes(
        router,
        user_administration_service_dependency=user_administration_service_dependency,
        own_password_service_dependency=own_password_service_dependency,
        require_admin_users_manage=require_admin_users_manage,
        cookie_csrf_protection=cookie_csrf_protection,
    )
    if entra_oidc_enabled:
        router.add_api_route(
            "/entra/start",
            start_entra_login,
            methods=["GET"],
            response_class=RedirectResponse,
        )
        router.add_api_route(
            "/entra/callback",
            complete_entra_login,
            methods=["GET"],
            response_class=RedirectResponse,
        )
    return router


def _set_session_cookie(
    response: Response,
    *,
    session: UserSession,
    token: OpaqueSessionToken,
) -> None:
    max_age = int(
        (session.expires_at - session.created_at).total_seconds(),
    )
    response.set_cookie(
        key=DOCMIND_SESSION_COOKIE,
        value=token.value,
        max_age=max_age,
        path="/",
        secure=True,
        httponly=True,
        samesite="lax",
    )


def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        key=DOCMIND_SESSION_COOKIE,
        path="/",
        secure=True,
        httponly=True,
        samesite="lax",
    )


def _set_refresh_cookie(
    response: Response,
    *,
    refresh_token_record: SessionRefreshToken,
    token: OpaqueRefreshToken,
) -> None:
    max_age = int(
        (refresh_token_record.expires_at - refresh_token_record.created_at).total_seconds(),
    )
    response.set_cookie(
        key=DOCMIND_REFRESH_COOKIE,
        value=token.value,
        max_age=max_age,
        path="/",
        secure=True,
        httponly=True,
        samesite="lax",
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=DOCMIND_REFRESH_COOKIE,
        path="/",
        secure=True,
        httponly=True,
        samesite="lax",
    )


def _invalid_refresh_token_response() -> JSONResponse:
    error = InvalidRefreshTokenError()
    response = JSONResponse(
        status_code=error.status_code,
        content={
            "error": {
                "code": error.code,
                "details": dict(error.details),
                "message": error.message,
            },
        },
    )
    _clear_session_cookie(response)
    _clear_refresh_cookie(response)
    return response


def _entra_oidc_callback_rejected_response(
    error: EntraOidcCallbackRejectedError,
) -> JSONResponse:
    response = JSONResponse(
        status_code=error.status_code,
        content={
            "error": {
                "code": error.code,
                "details": dict(error.details),
                "message": error.message,
            },
        },
    )
    _clear_entra_oidc_browser_binding_cookie(response)
    return response


def _set_entra_oidc_browser_binding_cookie(
    response: Response,
    *,
    browser_binding: str,
    max_age: int,
) -> None:
    response.set_cookie(
        key=ENTRA_OIDC_BROWSER_BINDING_COOKIE,
        value=browser_binding,
        max_age=max_age,
        path="/",
        secure=True,
        httponly=True,
        samesite="lax",
    )


def _clear_entra_oidc_browser_binding_cookie(response: Response) -> None:
    response.delete_cookie(
        key=ENTRA_OIDC_BROWSER_BINDING_COOKIE,
        path="/",
        secure=True,
        httponly=True,
        samesite="lax",
    )


def _to_current_actor_envelope(actor: AuthenticatedActor) -> CurrentActorEnvelope:
    return CurrentActorEnvelope(data=_to_current_actor_schema(actor))


def _to_current_actor_schema(actor: AuthenticatedActor) -> CurrentActorSchema:
    return CurrentActorSchema(
        auth_providers=sorted(actor.auth_providers, key=lambda provider: provider.value),
        provider=actor.provider,
        user_id=actor.actor_id,
        email=actor.email,
        roles=sorted(actor.roles, key=lambda role: role.value),
        permissions=sorted(actor.permissions, key=lambda permission: permission.value),
    )


def _to_csrf_token_schema(token: str) -> CsrfTokenSchema:
    return CsrfTokenSchema(token=token, header_name=CSRF_HEADER)
