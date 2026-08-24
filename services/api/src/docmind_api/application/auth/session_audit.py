"""Audit helpers for browser session application flows."""

import logging

from docmind_api.domain.auth.sessions import SessionRevocationReason
from docmind_backend_runtime.context import get_correlation_id

_AUTH_AUDIT_LOGGER = logging.getLogger("docmind_api.auth.audit")


def log_session_revoked(
    *,
    actor_id: str,
    target_user_id: str,
    session_id: str,
    reason: SessionRevocationReason,
) -> None:
    """Log an audit-safe session revocation event."""

    _AUTH_AUDIT_LOGGER.info(
        "User session revoked.",
        extra={
            "auth_boundary": "browser_session",
            "auth_decision": "session_revoked",
            "actor_id": actor_id,
            "target_user_id": target_user_id,
            "session_id": session_id,
            "revocation_reason": reason.value,
            "correlation_id": get_correlation_id(),
        },
    )


def log_refresh_credentials_revoked(
    *,
    actor_id: str | None,
    target_user_id: str | None,
    session_id: str | None,
    refresh_token_family_id: str | None,
    reason: SessionRevocationReason,
) -> None:
    """Log an audit-safe refresh credential revocation event."""

    _AUTH_AUDIT_LOGGER.info(
        "Refresh credentials revoked.",
        extra={
            "auth_boundary": "browser_session",
            "auth_decision": "refresh_credentials_revoked",
            "actor_id": actor_id,
            "target_user_id": target_user_id,
            "session_id": session_id,
            "refresh_token_family_id": refresh_token_family_id,
            "revocation_reason": reason.value,
            "correlation_id": get_correlation_id(),
        },
    )


def log_refresh_token_reuse_detected(
    *,
    target_user_id: str | None,
    session_id: str | None,
    refresh_token_id: str,
    refresh_token_family_id: str,
) -> None:
    """Log an audit-safe refresh token reuse event."""

    _AUTH_AUDIT_LOGGER.warning(
        "Refresh token reuse detected.",
        extra={
            "auth_boundary": "browser_session",
            "auth_decision": "refresh_token_reuse_detected",
            "actor_id": None,
            "target_user_id": target_user_id,
            "session_id": session_id,
            "refresh_token_id": refresh_token_id,
            "refresh_token_family_id": refresh_token_family_id,
            "correlation_id": get_correlation_id(),
        },
    )
