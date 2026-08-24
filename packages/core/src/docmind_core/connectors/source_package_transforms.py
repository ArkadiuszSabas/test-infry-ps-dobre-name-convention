"""Fail-closed transformations applied inside a source-package staging tree."""

from __future__ import annotations

import hashlib
import shutil
from dataclasses import dataclass
from pathlib import Path

from docmind_core.connectors.profiles import DeploymentProfile, ProfileValidationError


@dataclass(frozen=True, slots=True)
class MaterializedOverlayFile:
    """One overlay file copied to its customer-repository destination."""

    source: str
    destination: str
    sha256: str


def materialize_profile_overlay(
    *,
    staging_root: Path,
    profile: DeploymentProfile,
) -> tuple[MaterializedOverlayFile, ...]:
    """Copy a profile-owned overlay to the snapshot root and remove its staging source."""

    configured_path = profile.source_package.overlay_path
    if configured_path is None:
        return ()

    overlay_relative = Path(configured_path)
    expected_root = Path("deployments") / profile.profile_id / "source-overlay"
    if overlay_relative != expected_root:
        raise ProfileValidationError(
            "source_package.overlay_path must equal "
            f"'{expected_root.as_posix()}' for profile '{profile.profile_id}'.",
        )

    resolved_staging_root = staging_root.resolve(strict=True)
    overlay_root = (resolved_staging_root / overlay_relative).resolve(strict=True)
    if not overlay_root.is_relative_to(resolved_staging_root) or not overlay_root.is_dir():
        raise ProfileValidationError(
            f"Source-package overlay directory is invalid: {configured_path}.",
        )

    materialized: list[MaterializedOverlayFile] = []
    for source_path in sorted(path for path in overlay_root.rglob("*") if path.is_file()):
        relative_path = source_path.relative_to(overlay_root)
        _validate_overlay_destination(relative_path=relative_path, profile=profile)
        destination_path = (resolved_staging_root / relative_path).resolve(strict=False)
        if not destination_path.is_relative_to(resolved_staging_root):
            raise ProfileValidationError(
                f"Source-package overlay destination escapes the snapshot: {relative_path}.",
            )
        if destination_path.exists():
            raise ProfileValidationError(
                f"Source-package overlay cannot replace an allowlisted file: {relative_path}.",
            )
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_path, destination_path)
        materialized.append(
            MaterializedOverlayFile(
                source=source_path.relative_to(resolved_staging_root).as_posix(),
                destination=relative_path.as_posix(),
                sha256=_sha256(destination_path),
            ),
        )

    shutil.rmtree(overlay_root)
    return tuple(materialized)


def _validate_overlay_destination(
    *,
    relative_path: Path,
    profile: DeploymentProfile,
) -> None:
    reserved_profile_path = Path("deployments") / profile.profile_id / "profile.yml"
    if (
        not relative_path.parts
        or relative_path.parts[0] in {".git", "generated"}
        or ".terraform" in relative_path.parts
        or relative_path == reserved_profile_path
    ):
        raise ProfileValidationError(
            f"Source-package overlay targets a reserved snapshot path: {relative_path}.",
        )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source_file:
        for chunk in iter(lambda: source_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
