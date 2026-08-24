"""Command-line entrypoint for applying approved API schema migrations."""

import re
import sys
from collections.abc import Callable, Sequence
from urllib.parse import urlsplit, urlunsplit

from alembic.command import upgrade
from alembic.config import Config

from docmind_api.infrastructure.persistence.migrations import create_migrations_config
from docmind_api.settings import DatabaseSettings, get_database_settings

_MIGRATION_TARGET_REVISION = "head"
_MAX_ERROR_DETAIL_CHARS = 2000
_POSTGRESQL_URL_PATTERN = re.compile(
    r"\bpostgres(?:ql)?(?:\+asyncpg)?://[^@\r\n]+@[^\s'\",;)}\]]+",
    re.IGNORECASE,
)
_POSTGRESQL_CREDENTIAL_FRAGMENT_PATTERN = re.compile(
    r"\b(?P<scheme>postgres(?:ql)?(?:\+asyncpg)?)://[^@\r\n]+@",
    re.IGNORECASE,
)
_SENSITIVE_ERROR_FRAGMENT_PATTERN = re.compile(
    r"(?P<key>[\"']?\b(?:password|pwd|access[-_ ]?token|refresh[-_ ]?token|"
    r"client[-_ ]?secret|secret|credential)[a-z0-9_-]*\b[\"']?)"
    r"(?P<sep>\s*[:=]\s*)"
    r"(?P<value>\"[^\"]*\"|'[^']*'|[^,;}\]\r\n]+)",
    re.IGNORECASE,
)


def main(argv: Sequence[str] | None = None) -> int:
    """Apply API Alembic migrations from the command line."""

    argv = sys.argv[1:] if argv is None else argv
    if argv:
        sys.stderr.write("API migrations do not accept command-line arguments.\n")
        return 2

    try:
        _apply_migrations(
            settings=get_database_settings(),
            upgrade_command=upgrade,
        )
    except Exception as error:
        error_detail = _sanitize_error_detail(str(error))
        sys.stderr.write(
            f"API migration failed. error_type={type(error).__name__}; detail={error_detail}\n",
        )
        return 2

    sys.stdout.write("API migrations applied successfully.\n")
    return 0


def _apply_migrations(
    *,
    settings: DatabaseSettings,
    upgrade_command: Callable[[Config, str], None],
) -> None:
    sys.stdout.write(
        "Applying API migrations "
        f"target={_MIGRATION_TARGET_REVISION} database={settings.redacted_url}\n",
    )
    upgrade_command(
        create_migrations_config(database_url=settings.url),
        _MIGRATION_TARGET_REVISION,
    )


def _sanitize_error_detail(error_detail: str) -> str:
    sanitized = _POSTGRESQL_URL_PATTERN.sub(
        _redact_postgresql_url_credentials,
        error_detail,
    )
    sanitized = _POSTGRESQL_CREDENTIAL_FRAGMENT_PATTERN.sub(
        _redact_postgresql_credential_fragment,
        sanitized,
    )
    sanitized = _SENSITIVE_ERROR_FRAGMENT_PATTERN.sub(_redact_sensitive_fragment, sanitized)
    sanitized = sanitized.strip()
    if not sanitized:
        return "sensitive details omitted"
    return sanitized[:_MAX_ERROR_DETAIL_CHARS]


def _redact_postgresql_url_credentials(match: re.Match[str]) -> str:
    raw_url = match.group(0)
    try:
        parsed_url = urlsplit(raw_url)
    except ValueError:
        scheme = raw_url.split("://", 1)[0]
        return f"{scheme}://***"

    userinfo, separator, hostinfo = parsed_url.netloc.rpartition("@")
    if not separator:
        return raw_url

    redacted_userinfo = "***:***" if ":" in userinfo else "***"
    return urlunsplit(
        (
            parsed_url.scheme,
            f"{redacted_userinfo}@{hostinfo}",
            parsed_url.path,
            parsed_url.query,
            parsed_url.fragment,
        ),
    )


def _redact_postgresql_credential_fragment(match: re.Match[str]) -> str:
    return f"{match.group('scheme')}://***@"


def _redact_sensitive_fragment(match: re.Match[str]) -> str:
    return f"{match.group('key')}{match.group('sep')}***"


if __name__ == "__main__":
    raise SystemExit(main())
