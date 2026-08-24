"""HTTP response mappers for auth session management."""

from datetime import datetime

from docmind_api.api.auth.schemas import (
    ManagedBrowserSessionSchema,
    UserSessionListEnvelope,
    UserSessionListSchema,
    UserSessionRevocationEnvelope,
    UserSessionRevocationSchema,
)
from docmind_api.application.auth.session_management import (
    ManagedUserSessionRevocationResult,
    UserSessionListResult,
)
from docmind_api.domain.auth.sessions import UserSession


def to_session_list_envelope(result: UserSessionListResult) -> UserSessionListEnvelope:
    """Map an application session list result to the public HTTP envelope."""

    return UserSessionListEnvelope(
        data=UserSessionListSchema(
            sessions=[
                to_managed_session_schema(session, evaluated_at=result.evaluated_at)
                for session in result.sessions
            ],
        ),
        meta={"evaluated_at": result.evaluated_at},
    )


def to_session_revocation_envelope(
    result: ManagedUserSessionRevocationResult,
) -> UserSessionRevocationEnvelope:
    """Map an application revocation result to the public HTTP envelope."""

    return UserSessionRevocationEnvelope(
        data=UserSessionRevocationSchema(
            revoked=result.revoked,
            session=to_managed_session_schema(
                result.session,
                evaluated_at=result.evaluated_at,
            ),
        ),
        meta={"evaluated_at": result.evaluated_at},
    )


def to_managed_session_schema(
    session: UserSession,
    *,
    evaluated_at: datetime,
) -> ManagedBrowserSessionSchema:
    """Map a session domain model without exposing token material."""

    return ManagedBrowserSessionSchema(
        id=str(session.id),
        user_id=str(session.user_id),
        provider=session.auth_provider,
        status=session.status_at(evaluated_at),
        created_at=session.created_at,
        last_seen_at=session.last_seen_at,
        expires_at=session.expires_at,
        revoked_at=session.revoked_at,
        revoked_reason=session.revoked_reason,
        client_label=session.client_label,
        client_fingerprint=session.client_fingerprint.value
        if session.client_fingerprint is not None
        else None,
    )
