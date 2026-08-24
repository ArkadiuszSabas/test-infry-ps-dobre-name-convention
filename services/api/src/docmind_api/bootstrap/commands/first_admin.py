"""Command-line entrypoint for first local administrator bootstrap."""

import argparse
import asyncio
import getpass
import sys
from collections.abc import Sequence
from os import environ

from docmind_api.application.auth.first_admin_bootstrap import (
    BootstrapFirstAdminCommand,
    BootstrapFirstAdminOutcome,
    BootstrapFirstAdminResult,
    BootstrapFirstAdminUseCase,
)
from docmind_api.application.auth.local_accounts import LocalUserService
from docmind_api.infrastructure.auth.local.password_hashing import Argon2idPasswordHasher
from docmind_api.infrastructure.auth.runtime import UtcClock, UuidIdGenerator
from docmind_api.infrastructure.persistence.auth.repositories import (
    SqlAlchemyFirstAdminBootstrapRepository,
    SqlAlchemyLocalUserRepository,
)
from docmind_api.infrastructure.persistence.sql import (
    create_database_engine,
    create_database_session_factory,
    database_session_scope,
)
from docmind_api.settings import get_database_settings
from docmind_backend_runtime.errors import ApplicationError

_DEFAULT_PASSWORD_ENV = "DOCMIND_API_FIRST_ADMIN_PASSWORD"
_DEFAULT_LOGIN_ENV = "DOCMIND_API_FIRST_ADMIN_LOGIN"
_DEFAULT_DISPLAY_NAME_ENV = "DOCMIND_API_FIRST_ADMIN_DISPLAY_NAME"


class FirstAdminCommandError(RuntimeError):
    """Raised when command-line input cannot safely bootstrap the first admin."""


def main(argv: Sequence[str] | None = None) -> int:
    """Run first local administrator bootstrap from the command line."""

    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        login = _resolve_required_text(
            argument=args.login,
            environment_variable=args.login_env,
            label="First admin login",
        )
        display_name = _resolve_required_text(
            argument=args.display_name,
            environment_variable=args.display_name_env,
            label="First admin display name",
        )
        plaintext_password = _resolve_password(password_env=args.password_env)
        result = asyncio.run(
            bootstrap_first_admin(
                login=login,
                display_name=display_name,
                plaintext_password=plaintext_password,
            ),
        )
    except (ApplicationError, FirstAdminCommandError, RuntimeError, ValueError) as error:
        sys.stderr.write(f"{error}\n")
        return 2

    if result.outcome == BootstrapFirstAdminOutcome.ADMIN_ALREADY_EXISTS:
        sys.stdout.write("A DocMind admin already exists; no changes were made.\n")
        return 0

    if result.user is None:
        sys.stderr.write("First admin bootstrap did not return the created user.\n")
        return 2

    sys.stdout.write("Created first local DocMind admin.\n")
    return 0


async def bootstrap_first_admin(
    *,
    login: str,
    display_name: str,
    plaintext_password: str,
) -> BootstrapFirstAdminResult:
    """Create the first local administrator through production adapters."""

    engine = create_database_engine(get_database_settings())
    session_factory = create_database_session_factory(engine)
    try:
        async with database_session_scope(session_factory) as session:
            local_user_service = LocalUserService(
                repository=SqlAlchemyLocalUserRepository(session),
                password_hasher=Argon2idPasswordHasher(),
                clock=UtcClock(),
                id_generator=UuidIdGenerator(),
            )
            use_case = BootstrapFirstAdminUseCase(
                local_user_service=local_user_service,
                repository=SqlAlchemyFirstAdminBootstrapRepository(session),
            )
            return await use_case.execute(
                BootstrapFirstAdminCommand(
                    login=login,
                    display_name=display_name,
                    plaintext_password=plaintext_password,
                ),
            )
    finally:
        await engine.dispose()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Bootstrap the first local DocMind administrator.",
    )
    parser.add_argument("--login", help="Local admin login or email.")
    parser.add_argument("--display-name", help="Display name for the admin.")
    parser.add_argument(
        "--login-env",
        default=_DEFAULT_LOGIN_ENV,
        help=(
            "Environment variable containing the first admin login. "
            f"Defaults to {_DEFAULT_LOGIN_ENV}."
        ),
    )
    parser.add_argument(
        "--display-name-env",
        default=_DEFAULT_DISPLAY_NAME_ENV,
        help=(
            "Environment variable containing the first admin display name. "
            f"Defaults to {_DEFAULT_DISPLAY_NAME_ENV}."
        ),
    )
    parser.add_argument(
        "--password-env",
        default=_DEFAULT_PASSWORD_ENV,
        help=(
            "Environment variable containing the first admin password. "
            f"Defaults to {_DEFAULT_PASSWORD_ENV}."
        ),
    )
    return parser


def _resolve_required_text(
    *,
    argument: str | None,
    environment_variable: str,
    label: str,
) -> str:
    if argument is not None:
        if argument.strip():
            return argument
        raise FirstAdminCommandError(f"{label} cannot be empty.")

    value = environ.get(environment_variable)
    if value is not None and value.strip():
        return value

    option_name = label.removeprefix("First admin ").replace(" ", "-").lower()
    raise FirstAdminCommandError(f"Set --{option_name} or {environment_variable}.")


def _resolve_password(*, password_env: str) -> str:
    configured_password = environ.get(password_env)
    if configured_password is not None:
        _ensure_password_is_present(configured_password)
        return configured_password

    if not sys.stdin.isatty():
        raise FirstAdminCommandError(
            f"Set {password_env} or run the command from an interactive terminal.",
        )

    password = getpass.getpass("First admin password: ")
    repeated_password = getpass.getpass("Repeat first admin password: ")
    if password != repeated_password:
        raise FirstAdminCommandError("First admin passwords do not match.")
    _ensure_password_is_present(password)

    return password


def _ensure_password_is_present(plaintext_password: str) -> None:
    if not plaintext_password.strip():
        raise FirstAdminCommandError("First admin password cannot be empty.")


if __name__ == "__main__":
    raise SystemExit(main())
