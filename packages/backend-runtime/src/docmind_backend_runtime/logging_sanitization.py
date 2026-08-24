"""Log value and message sanitization helpers."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Final, cast

REDACTED: Final = "[redacted]"
SENSITIVE_KEY_PARTS: Final = (
    "authorization",
    "api_key",
    "apikey",
    "connection_string",
    "connectionstring",
    "cookie",
    "credential",
    "password",
    "secret",
    "token",
)
_SENSITIVE_MESSAGE_PATTERN: Final = re.compile(
    r"(?P<key>[\"']?\b(?:[a-z0-9_-]*(?:api[-_ ]?key|apikey|connection[-_ ]?string|"
    r"connectionstring|cookie|credential|password|secret|token)[a-z0-9_-]*)\b[\"']?)"
    r"(?P<sep>\s*[:=]\s*)"
    r"(?P<value>\"[^\"]*\"|'[^']*'|[^\s,}\]]+)",
    re.IGNORECASE,
)
_AUTHORIZATION_MESSAGE_PATTERN: Final = re.compile(
    r"(?P<key>[\"']?\bauthorization\b[\"']?)"
    r"(?P<sep>\s*[:=]\s*)"
    r"(?P<value>\"(?:Bearer|Basic)\s+[^\"]*\"|'(?:Bearer|Basic)\s+[^']*'|"
    r"(?:Bearer|Basic)\s+[^\s,}\]]+|\"[^\"]*\"|'[^']*'|[^\s,}\]]+)",
    re.IGNORECASE,
)


def sanitize_log_value(key: str, value: object) -> object:
    """Return a log-safe value with sensitive fields redacted."""

    if is_sensitive_key(key):
        return REDACTED

    if isinstance(value, str):
        return sanitize_log_message(value)

    if isinstance(value, int | float | bool) or value is None:
        return value

    if isinstance(value, Mapping):
        mapping = cast(Mapping[object, object], value)
        return {
            str(nested_key): sanitize_log_value(str(nested_key), nested_value)
            for nested_key, nested_value in mapping.items()
        }

    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        sequence = cast(Sequence[object], value)
        return [sanitize_log_value(key, nested_value) for nested_value in sequence]

    return str(value)


def sanitize_log_message(message: str) -> str:
    """Redact obvious key-value sensitive fragments from free-form log messages."""

    message = _AUTHORIZATION_MESSAGE_PATTERN.sub(_redact_message_match, message)
    return _SENSITIVE_MESSAGE_PATTERN.sub(_redact_message_match, message)


def is_sensitive_key(key: str) -> bool:
    normalized_key = key.lower().replace("-", "_").replace(" ", "_")
    return any(part in normalized_key for part in SENSITIVE_KEY_PARTS)


def _redact_message_match(match: re.Match[str]) -> str:
    return f"{match.group('key')}{match.group('sep')}{REDACTED}"
