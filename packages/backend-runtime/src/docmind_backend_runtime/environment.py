"""Environment file loading and process environment access helpers."""

import re
import tomllib
from collections.abc import Mapping
from os import environ
from pathlib import Path
from typing import Final, cast

from dotenv import dotenv_values

_ENV_NAME_PATTERN: Final = re.compile(r"^[A-Z0-9_]+$")
_ENV_FILE_IGNORED_NAMES: Final = frozenset(
    {
        "DAPR_HTTP_ENDPOINT",
        "DAPR_HTTP_PORT",
        "DAPR_RUNTIME_HOST",
    },
)


def load_environment_files() -> None:
    """Load optional local environment files without overriding process variables."""

    for env_dir in _env_file_directories():
        for file_name in (".env.local", ".env"):
            env_path = env_dir / file_name
            if env_path.is_file():
                _load_environment_file(env_path)


def get_environment_variable(name: str) -> str | None:
    """Return a non-blank environment value after loading optional local env files."""

    load_environment_files()
    return read_environment_variable(name)


def require_environment_variable(name: str) -> str:
    """Return a required non-blank environment value."""

    value = get_environment_variable(name)
    if value is None:
        raise RuntimeError(f"Missing required environment variable: {name}")

    return value


def read_environment_variable(name: str) -> str | None:
    """Return a non-blank value from the current process environment."""

    value = environ.get(_normalize_environment_name(name))
    if value is None:
        return None

    stripped_value = value.strip()
    return stripped_value or None


def _env_file_directories() -> tuple[Path, ...]:
    cwd = Path.cwd().resolve()
    repository_root = _find_repository_root(cwd)
    candidates = (repository_root, cwd)
    directories: list[Path] = []
    seen: set[str] = set()

    for candidate in candidates:
        if candidate is None:
            continue
        candidate_key = str(candidate)
        if candidate_key in seen:
            continue
        seen.add(candidate_key)
        directories.append(candidate)

    return tuple(directories)


def _load_environment_file(env_path: Path) -> None:
    for name, value in dotenv_values(env_path).items():
        if value is None or name in _ENV_FILE_IGNORED_NAMES or name in environ:
            continue

        environ[name] = value


def _find_repository_root(start: Path) -> Path | None:
    current = start if start.is_dir() else start.parent
    for candidate in (current, *current.parents):
        if _is_workspace_root(candidate / "pyproject.toml"):
            return candidate

    return None


def _is_workspace_root(pyproject_path: Path) -> bool:
    if not pyproject_path.is_file():
        return False

    try:
        pyproject = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    except OSError:
        return False
    except tomllib.TOMLDecodeError:
        return False

    tool = pyproject.get("tool")
    if not isinstance(tool, Mapping):
        return False

    uv = cast(Mapping[str, object], tool).get("uv")
    if not isinstance(uv, Mapping):
        return False

    workspace = cast(Mapping[str, object], uv).get("workspace")
    return isinstance(workspace, Mapping)


def _normalize_environment_name(name: str) -> str:
    normalized_name = name.strip().upper()
    if not normalized_name or not _ENV_NAME_PATTERN.fullmatch(normalized_name):
        raise ValueError(
            "Environment variable names must contain only uppercase letters, "
            "digits, and underscores.",
        )

    return normalized_name
