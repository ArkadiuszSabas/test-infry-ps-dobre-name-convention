"""Privacy-aware HTTP client metadata helpers for auth sessions."""

import hashlib

from fastapi import Request

from docmind_api.domain.auth.sessions import (
    SessionClientFingerprint,
    SessionClientMetadata,
)


def session_client_metadata(request: Request) -> SessionClientMetadata:
    """Return response-safe client metadata derived from an HTTP request."""

    user_agent = request.headers.get("user-agent")
    client_host = request.client.host if request.client is not None else None
    return SessionClientMetadata(
        client_label=_client_label(user_agent),
        client_fingerprint=_client_fingerprint(
            user_agent=user_agent,
            client_host=client_host,
        ),
    )


def _client_label(user_agent: str | None) -> str:
    if user_agent is None or not user_agent.strip():
        return "Unknown client"

    normalized = user_agent.lower()
    browser = "Browser"
    if "edg/" in normalized:
        browser = "Edge"
    elif "firefox/" in normalized:
        browser = "Firefox"
    elif "chrome/" in normalized or "chromium/" in normalized:
        browser = "Chrome"
    elif "safari/" in normalized:
        browser = "Safari"

    platform = None
    if "windows" in normalized:
        platform = "Windows"
    elif "mac os" in normalized or "macintosh" in normalized:
        platform = "macOS"
    elif "android" in normalized:
        platform = "Android"
    elif "iphone" in normalized or "ipad" in normalized:
        platform = "iOS"
    elif "linux" in normalized:
        platform = "Linux"

    if platform is None:
        return browser

    return f"{browser} on {platform}"


def _client_fingerprint(
    *,
    user_agent: str | None,
    client_host: str | None,
) -> SessionClientFingerprint | None:
    normalized_user_agent = (user_agent or "").strip().lower()
    normalized_client_host = (client_host or "").strip().lower()
    if not normalized_user_agent and not normalized_client_host:
        return None

    fingerprint_material = f"{normalized_client_host}|{normalized_user_agent}"
    digest = hashlib.sha256(fingerprint_material.encode("utf-8")).hexdigest()
    return SessionClientFingerprint(f"sha256:{digest[:24]}")
