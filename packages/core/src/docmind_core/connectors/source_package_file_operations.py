"""Filesystem safety helpers for customer source-package materialization."""

from __future__ import annotations

import hashlib
import os
import shutil
from collections.abc import Mapping
from pathlib import Path
from typing import BinaryIO

from docmind_core.connectors.profiles import DeploymentProfile, ProfileValidationError


def validate_customer_scope_paths(
    *,
    profile: DeploymentProfile,
    source_files: tuple[str, ...],
) -> None:
    """Reject connector and deployment paths outside the selected customer profile."""

    allowed_connector_folders = {module.connector_folder for module in profile.installed_modules}
    for relative_text in source_files:
        parts = Path(relative_text).parts
        if len(parts) >= 4 and parts[:2] == ("packages", "connectors"):
            connector_root = parts[2]
            if connector_root != "src" and connector_root not in allowed_connector_folders:
                raise ProfileValidationError(
                    "Source snapshot contains an uninstalled connector folder: "
                    f"{connector_root} ({relative_text}).",
                )
        if parts and parts[0] == "deployments":
            if len(parts) < 3 or parts[1] != profile.profile_id:
                raise ProfileValidationError(
                    "Source snapshot contains deployment files outside profile "
                    f"{profile.profile_id}: {relative_text}.",
                )


def validate_output_path(*, output_path: Path, repo_root: Path | None = None) -> None:
    """Require a new output leaf that cannot replace the repository or an ancestor."""

    if output_path.name in {"", ".", ".."}:
        raise ProfileValidationError(
            f"Source package output path must name a new directory: {output_path}",
        )
    if output_path.exists() or output_path.is_symlink() or output_path.is_junction():
        raise ProfileValidationError(
            f"Source package output path already exists: {output_path}",
        )
    if repo_root is not None and (
        output_path == repo_root or repo_root.is_relative_to(output_path)
    ):
        raise ProfileValidationError(
            "Source package output path must not be the repository root or its ancestor.",
        )


def copy_source_files(
    *,
    repo_root: Path,
    staging_root: Path,
    source_files: tuple[str, ...],
    source_hashes: Mapping[str, str],
    profile: DeploymentProfile,
) -> None:
    """Copy validated regular files without following swapped links."""

    for relative_text in source_files:
        relative_path = Path(relative_text)
        if relative_path.is_absolute() or ".." in relative_path.parts:
            raise ProfileValidationError(
                f"Source snapshot contains an unsafe path: {relative_text}",
            )
        source_path = repo_root / relative_path
        if _path_contains_link(repo_root=repo_root, relative_path=relative_path):
            raise ProfileValidationError(
                "Source snapshot paths must not contain symbolic links or junctions: "
                f"{relative_text}",
            )
        try:
            resolved_source_path = source_path.resolve(strict=True)
        except OSError as error:
            raise ProfileValidationError(
                f"Source snapshot file cannot be resolved: {relative_text}",
            ) from error
        if not resolved_source_path.is_relative_to(repo_root) or not resolved_source_path.is_file():
            raise ProfileValidationError(
                f"Source snapshot file is outside the repository: {relative_text}",
            )
        validate_customer_scope_paths(
            profile=profile,
            source_files=(resolved_source_path.relative_to(repo_root).as_posix(),),
        )

        destination_path = staging_root / relative_path
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        _copy_source_file(
            source_path=resolved_source_path,
            destination_path=destination_path,
            repo_root=repo_root,
            relative_path=relative_path,
            relative_text=relative_text,
            expected_hash=source_hashes[relative_text],
        )


def source_file_hashes(
    *,
    repo_root: Path,
    source_files: tuple[str, ...],
) -> Mapping[str, str]:
    """Hash link-free source files for later copy-integrity verification."""

    hashes: dict[str, str] = {}
    for relative_text in source_files:
        relative_path = Path(relative_text)
        if _path_contains_link(repo_root=repo_root, relative_path=relative_path):
            raise ProfileValidationError(
                "Source snapshot paths must not contain symbolic links or junctions: "
                f"{relative_text}",
            )
        try:
            hashes[relative_text] = _sha256_source_file(
                source_path=repo_root / relative_path,
                repo_root=repo_root,
                relative_path=relative_path,
                relative_text=relative_text,
            )
        except OSError as error:
            raise ProfileValidationError(
                f"Source snapshot file could not be hashed: {relative_text}",
            ) from error
        if _path_contains_link(repo_root=repo_root, relative_path=relative_path):
            raise ProfileValidationError(
                "Source snapshot paths must not contain symbolic links or junctions: "
                f"{relative_text}",
            )
    return hashes


def _sha256_source_file(
    *,
    source_path: Path,
    repo_root: Path,
    relative_path: Path,
    relative_text: str,
) -> str:
    digest = hashlib.sha256()
    with source_path.open("rb") as source_file:
        _validate_open_source_file(
            source_file=source_file,
            source_path=source_path,
            repo_root=repo_root,
            relative_path=relative_path,
            relative_text=relative_text,
        )
        for chunk in iter(lambda: source_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _copy_source_file(
    *,
    source_path: Path,
    destination_path: Path,
    repo_root: Path,
    relative_path: Path,
    relative_text: str,
    expected_hash: str,
) -> None:
    try:
        with source_path.open("rb") as source_file:
            _validate_open_source_file(
                source_file=source_file,
                source_path=source_path,
                repo_root=repo_root,
                relative_path=relative_path,
                relative_text=relative_text,
            )
            with destination_path.open("xb") as destination_file:
                shutil.copyfileobj(source_file, destination_file)
    except OSError as error:
        raise ProfileValidationError(
            f"Source snapshot file could not be copied: {relative_text}",
        ) from error
    if _sha256(destination_path) != expected_hash:
        raise ProfileValidationError(
            f"Source snapshot file changed during materialization: {relative_text}",
        )


def _validate_open_source_file(
    *,
    source_file: BinaryIO,
    source_path: Path,
    repo_root: Path,
    relative_path: Path,
    relative_text: str,
) -> None:
    if _path_contains_link(repo_root=repo_root, relative_path=relative_path):
        raise ProfileValidationError(
            f"Source snapshot paths must not contain symbolic links or junctions: {relative_text}",
        )
    try:
        path_stat = source_path.stat(follow_symlinks=False)
        handle_stat = os.fstat(source_file.fileno())
    except OSError as error:
        raise ProfileValidationError(
            f"Source snapshot file could not be verified: {relative_text}",
        ) from error
    if not os.path.samestat(path_stat, handle_stat):
        raise ProfileValidationError(
            f"Source snapshot file changed during materialization: {relative_text}",
        )


def _path_contains_link(*, repo_root: Path, relative_path: Path) -> bool:
    candidate = repo_root
    for part in relative_path.parts:
        candidate /= part
        if candidate.is_symlink() or candidate.is_junction():
            return True
    return False


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source_file:
        for chunk in iter(lambda: source_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
