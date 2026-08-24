"""Invitation domain models for admin-owned user onboarding."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from docmind_api.domain.auth.actors import Role

INVITATION_EMAIL_MAX_LENGTH = 320


class InvitationStatus(StrEnum):
    """Lifecycle state for an admin-created user invitation."""

    PENDING = "pending"
    CANCELLED = "cancelled"
    ACCEPTED = "accepted"


@dataclass(frozen=True, slots=True)
class InvitationTokenHash:
    """Persisted one-time invitation token hash."""

    value: str

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise ValueError("Invitation token hash cannot be empty.")


@dataclass(frozen=True, slots=True)
class UserInvitation:
    """Admin onboarding invitation without raw token material."""

    id: UUID
    email: str
    roles: tuple[Role, ...]
    token_hash: InvitationTokenHash
    status: InvitationStatus
    created_by_user_id: UUID
    created_at: datetime
    updated_at: datetime
    expires_at: datetime
    cancelled_at: datetime | None = None
    cancelled_by_user_id: UUID | None = None
    accepted_at: datetime | None = None
    accepted_by_user_id: UUID | None = None

    def __post_init__(self) -> None:
        normalized_email = normalize_invitation_email(self.email)
        if normalized_email != self.email:
            raise ValueError("Invitation email must be normalized.")
        if not self.roles:
            raise ValueError("Invitation must include at least one role.")
        if tuple(sorted(set(self.roles), key=lambda role: role.value)) != self.roles:
            raise ValueError("Invitation roles must be unique and sorted.")
        if self.created_at > self.updated_at:
            raise ValueError("Invitation updated_at cannot be before created_at.")
        if self.created_at >= self.expires_at:
            raise ValueError("Invitation expires_at must be after created_at.")
        if self.status == InvitationStatus.CANCELLED:
            if self.cancelled_at is None or self.cancelled_by_user_id is None:
                raise ValueError("Cancelled invitation requires cancellation metadata.")
        if self.status != InvitationStatus.CANCELLED:
            if self.cancelled_at is not None or self.cancelled_by_user_id is not None:
                raise ValueError("Only cancelled invitations may include cancellation metadata.")
        if self.status == InvitationStatus.ACCEPTED:
            if self.accepted_at is None or self.accepted_by_user_id is None:
                raise ValueError("Accepted invitation requires acceptance metadata.")
        if self.status != InvitationStatus.ACCEPTED:
            if self.accepted_at is not None or self.accepted_by_user_id is not None:
                raise ValueError("Only accepted invitations may include acceptance metadata.")

    def cancel(self, *, cancelled_at: datetime, cancelled_by_user_id: UUID) -> UserInvitation:
        """Return the cancelled invitation state."""

        if self.status != InvitationStatus.PENDING:
            return self
        if cancelled_at < self.created_at:
            raise ValueError("Invitation cancelled_at cannot be before created_at.")

        return UserInvitation(
            id=self.id,
            email=self.email,
            roles=self.roles,
            token_hash=self.token_hash,
            status=InvitationStatus.CANCELLED,
            created_by_user_id=self.created_by_user_id,
            created_at=self.created_at,
            updated_at=cancelled_at,
            expires_at=self.expires_at,
            cancelled_at=cancelled_at,
            cancelled_by_user_id=cancelled_by_user_id,
            accepted_at=None,
            accepted_by_user_id=None,
        )

    def is_pending_at(self, evaluated_at: datetime) -> bool:
        """Return whether the invitation can still be acted on as pending."""

        return self.status == InvitationStatus.PENDING and self.expires_at > evaluated_at


def normalize_invitation_email(email: str) -> str:
    """Normalize an invitation email for uniqueness and matching."""

    normalized = email.strip().lower()
    if not normalized or "@" not in normalized or len(normalized) > INVITATION_EMAIL_MAX_LENGTH:
        raise ValueError("Invitation email is invalid.")
    return normalized


def normalize_invitation_roles(roles: tuple[Role, ...]) -> tuple[Role, ...]:
    """Return unique roles in stable API order."""

    if not roles:
        raise ValueError("Invitation must include at least one role.")
    return tuple(sorted(set(roles), key=lambda role: role.value))
