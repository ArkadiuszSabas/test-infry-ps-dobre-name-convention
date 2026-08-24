"""HTTP schemas for DocMind.ai auth endpoints."""

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field

from docmind_api.domain.auth.actors import AuthProvider, Permission, Role
from docmind_api.domain.auth.invitations import InvitationStatus
from docmind_api.domain.auth.sessions import SessionRevocationReason, UserSessionStatus
from docmind_api.domain.auth.users import UserStatus

CSRF_HEADER_NAME = "X-CSRF-Token"


class LocalLoginRequest(BaseModel):
    """HTTP request schema for local username/password login."""

    login: str
    password: str = Field(repr=False)


class CurrentActorSchema(BaseModel):
    """HTTP schema for the currently authenticated actor."""

    auth_providers: list[AuthProvider]
    provider: AuthProvider
    user_id: str
    email: str | None
    roles: list[Role]
    permissions: list[Permission]


class CurrentActorEnvelope(BaseModel):
    """Standard API response envelope for the current actor endpoint."""

    data: CurrentActorSchema
    meta: dict[str, str] = Field(default_factory=dict)


class BrowserSessionSchema(BaseModel):
    """HTTP schema for an API-owned browser session."""

    expires_at: datetime


class CsrfTokenSchema(BaseModel):
    """HTTP schema for a browser-readable CSRF token."""

    token: str = Field(repr=False)
    header_name: str = CSRF_HEADER_NAME


class LocalLoginSchema(BaseModel):
    """HTTP schema returned after a successful local login."""

    user: CurrentActorSchema
    session: BrowserSessionSchema
    csrf: CsrfTokenSchema


class LocalLoginEnvelope(BaseModel):
    """Standard API response envelope for local login."""

    data: LocalLoginSchema
    meta: dict[str, str] = Field(default_factory=dict)


class RefreshSessionSchema(BaseModel):
    """HTTP schema returned after a successful session refresh."""

    user: CurrentActorSchema
    session: BrowserSessionSchema


class RefreshSessionEnvelope(BaseModel):
    """Standard API response envelope for session refresh."""

    data: RefreshSessionSchema
    meta: dict[str, str] = Field(default_factory=dict)


class LogoutSchema(BaseModel):
    """HTTP schema returned after a logout request."""

    revoked: bool


class LogoutEnvelope(BaseModel):
    """Standard API response envelope for logout."""

    data: LogoutSchema
    meta: dict[str, str] = Field(default_factory=dict)


class ManagedBrowserSessionSchema(BaseModel):
    """HTTP schema for session management diagnostics."""

    id: str
    user_id: str
    provider: AuthProvider
    status: UserSessionStatus
    created_at: datetime
    last_seen_at: datetime
    expires_at: datetime
    revoked_at: datetime | None
    revoked_reason: SessionRevocationReason | None
    client_label: str | None
    client_fingerprint: str | None


class UserSessionListSchema(BaseModel):
    """HTTP schema returned when listing browser sessions."""

    sessions: list[ManagedBrowserSessionSchema]


class UserSessionListEnvelope(BaseModel):
    """Standard API response envelope for browser session lists."""

    data: UserSessionListSchema
    meta: dict[str, datetime] = Field(default_factory=dict)


class UserSessionRevocationSchema(BaseModel):
    """HTTP schema returned after revoking a managed session."""

    revoked: bool
    session: ManagedBrowserSessionSchema


class UserSessionRevocationEnvelope(BaseModel):
    """Standard API response envelope for managed session revocation."""

    data: UserSessionRevocationSchema
    meta: dict[str, datetime] = Field(default_factory=dict)


class CsrfTokenEnvelope(BaseModel):
    """Standard API response envelope for a CSRF token."""

    data: CsrfTokenSchema
    meta: dict[str, str] = Field(default_factory=dict)


class UserInvitationCreateRequest(BaseModel):
    """HTTP request schema for creating a user invitation."""

    email: str
    roles: list[Role]


class UserInvitationSchema(BaseModel):
    """HTTP schema for an admin-managed user invitation."""

    id: UUID
    email: str
    roles: list[Role]
    status: InvitationStatus
    created_by_user_id: UUID
    created_at: datetime
    updated_at: datetime
    expires_at: datetime
    cancelled_at: datetime | None
    cancelled_by_user_id: UUID | None
    accepted_at: datetime | None
    accepted_by_user_id: UUID | None


class UserInvitationListSchema(BaseModel):
    """HTTP schema returned when listing pending invitations."""

    invitations: list[UserInvitationSchema]


class UserInvitationEnvelope(BaseModel):
    """Standard API response envelope for a single invitation."""

    data: UserInvitationSchema
    meta: dict[str, datetime | bool] = Field(default_factory=dict)


class UserInvitationListEnvelope(BaseModel):
    """Standard API response envelope for invitation lists."""

    data: UserInvitationListSchema
    meta: dict[str, datetime | bool] = Field(default_factory=dict)


class ManagedUserSchema(BaseModel):
    """HTTP schema for an admin-managed user."""

    id: UUID
    display_name: str
    status: UserStatus
    roles: list[Role]
    auth_providers: list[AuthProvider]
    email: str | None
    created_at: datetime
    updated_at: datetime


class ManagedUserWritableStatus(StrEnum):
    """HTTP status values accepted by admin create and profile update routes."""

    ACTIVE = UserStatus.ACTIVE.value
    INACTIVE = UserStatus.INACTIVE.value


class ManagedUserListSchema(BaseModel):
    """HTTP schema returned when listing admin-managed users."""

    users: list[ManagedUserSchema]


class ManagedUserListMetaSchema(BaseModel):
    """HTTP metadata for admin-managed user lists."""

    evaluated_at: datetime
    total_count: int
    returned_count: int
    include_deleted: bool


class ManagedUserOperationMetaSchema(BaseModel):
    """HTTP metadata for one admin-managed user operation."""

    evaluated_at: datetime
    revoked_sessions: int = 0


class ManagedUserEnvelope(BaseModel):
    """Standard API response envelope for one admin-managed user."""

    data: ManagedUserSchema
    meta: ManagedUserOperationMetaSchema


class ManagedUserListEnvelope(BaseModel):
    """Standard API response envelope for admin-managed user lists."""

    data: ManagedUserListSchema
    meta: ManagedUserListMetaSchema


class CreateManagedLocalUserRequest(BaseModel):
    """HTTP request schema for admin-created local users."""

    login: str
    display_name: str
    password: str = Field(repr=False)
    roles: list[Role]
    status: ManagedUserWritableStatus = ManagedUserWritableStatus.ACTIVE


class UpdateManagedUserRequest(BaseModel):
    """HTTP request schema for admin-managed user updates."""

    display_name: str | None = None
    roles: list[Role] | None = None
    status: ManagedUserWritableStatus | None = None


class DeleteManagedUserSchema(BaseModel):
    """HTTP schema returned after a user is soft-deleted."""

    id: UUID
    deleted: bool


class DeleteManagedUserEnvelope(BaseModel):
    """Standard API response envelope for admin-managed user deletion."""

    data: DeleteManagedUserSchema
    meta: ManagedUserOperationMetaSchema


class SetManagedUserPasswordRequest(BaseModel):
    """HTTP request schema for admin-managed password changes."""

    new_password: str = Field(repr=False)


class SetManagedUserPasswordSchema(BaseModel):
    """HTTP schema returned after an admin-managed password change."""

    id: UUID
    changed: bool


class SetManagedUserPasswordEnvelope(BaseModel):
    """Standard API response envelope for admin-managed password changes."""

    data: SetManagedUserPasswordSchema
    meta: ManagedUserOperationMetaSchema


class ChangeOwnPasswordRequest(BaseModel):
    """HTTP request schema for changing the current user's password."""

    current_password: str = Field(repr=False)
    new_password: str = Field(repr=False)


class ChangeOwnPasswordSchema(BaseModel):
    """HTTP schema returned after changing the current user's password."""

    changed: bool


class ChangeOwnPasswordEnvelope(BaseModel):
    """Standard API response envelope for current-user password changes."""

    data: ChangeOwnPasswordSchema
    meta: ManagedUserOperationMetaSchema
