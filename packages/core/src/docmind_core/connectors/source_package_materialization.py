"""Materialize validated customer source-package snapshots."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from importlib import import_module
from pathlib import Path
from typing import cast

from docmind_core.connectors.profiles import (
    DeploymentProfile,
    ProfileManifest,
    ProfileValidationError,
    SourcePackageDeliveryTarget,
    SourcePackageProfile,
    deployment_profile_to_mapping,
    generate_profile_manifest,
    manifest_to_mapping,
)
from docmind_core.connectors.source_package import (
    SourceSnapshotManifest,
    build_source_snapshot_manifest,
    raise_for_source_snapshot_violations,
)
from docmind_core.connectors.source_package_file_operations import (
    copy_source_files,
    source_file_hashes,
    validate_customer_scope_paths,
    validate_output_path,
)
from docmind_core.connectors.source_package_transforms import materialize_profile_overlay

_PROFILE_MANIFEST_PATH = Path("generated/profile-manifest.json")
_SOURCE_SNAPSHOT_MANIFEST_PATH = Path("generated/source-snapshot-manifest.json")
_SOURCE_TRANSFORM_MANIFEST_PATH = Path("generated/source-transform-manifest.json")
_WINDOWS_PUBLISH_RETRY_DELAYS_SECONDS = (0.05, 0.1, 0.2, 0.4)


@dataclass(frozen=True, slots=True)
class SourcePackageMaterializationResult:
    """Summary of one successfully materialized customer snapshot."""

    output_path: Path
    source_version: str | None
    payload_files: tuple[str, ...]
    snapshot_manifest_path: str


@dataclass(frozen=True, slots=True)
class _ValidatedMaterializationInputs:
    manifest: ProfileManifest
    snapshot: SourceSnapshotManifest
    source_hashes: Mapping[str, str]


def materialize_source_package(
    *,
    repo_root: Path,
    output_path: Path,
    profile: DeploymentProfile,
    manifest: ProfileManifest,
    snapshot: SourceSnapshotManifest,
    source_version: str | None = None,
) -> SourcePackageMaterializationResult:
    """Write a validated customer snapshot without overwriting an existing path."""

    _validate_delivery_profile(profile)
    resolved_repo_root = repo_root.resolve(strict=True)
    validate_output_path(output_path=output_path)
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        resolved_output_parent = output_path.parent.resolve(strict=True)
    except OSError as error:
        raise ProfileValidationError(
            f"Source package output parent could not be prepared: {output_path.parent}",
        ) from error
    resolved_output_path = resolved_output_parent / output_path.name
    validate_output_path(
        repo_root=resolved_repo_root,
        output_path=resolved_output_path,
    )
    validated_inputs = _validate_materialization_inputs(
        repo_root=resolved_repo_root,
        profile=profile,
        manifest=manifest,
        snapshot=snapshot,
    )
    normalized_source_version = source_version.strip() if source_version else None
    if not normalized_source_version:
        normalized_source_version = None

    with tempfile.TemporaryDirectory(
        dir=resolved_output_parent,
        prefix=f".{resolved_output_path.name}.staging-",
    ) as temporary_directory:
        staging_root = Path(temporary_directory) / "snapshot"
        staging_root.mkdir()
        copy_source_files(
            repo_root=resolved_repo_root,
            staging_root=staging_root,
            source_files=validated_inputs.snapshot.files,
            source_hashes=validated_inputs.source_hashes,
            profile=profile,
        )
        overlay_files = materialize_profile_overlay(
            staging_root=staging_root,
            profile=profile,
        )
        _write_generated_profile(
            staging_root=staging_root,
            profile=profile,
        )
        _write_json(
            staging_root / _PROFILE_MANIFEST_PATH,
            manifest_to_mapping(validated_inputs.manifest),
        )
        _write_json(
            staging_root / _SOURCE_TRANSFORM_MANIFEST_PATH,
            {
                "schema_version": 1,
                "profile_id": profile.profile_id,
                "overlay_path": profile.source_package.overlay_path,
                "files": [
                    {
                        "source": item.source,
                        "destination": item.destination,
                        "sha256": item.sha256,
                    }
                    for item in overlay_files
                ],
            },
        )

        payload_files = _payload_file_paths(staging_root)
        _write_json(
            staging_root / _SOURCE_SNAPSHOT_MANIFEST_PATH,
            _source_snapshot_manifest_mapping(
                staging_root=staging_root,
                profile_id=profile.profile_id,
                payload_files=payload_files,
                source_version=normalized_source_version,
            ),
        )
        _scan_materialized_tree(
            staging_root=staging_root,
            manifest=validated_inputs.manifest,
        )

        if (
            resolved_output_path.exists()
            or resolved_output_path.is_symlink()
            or resolved_output_path.is_junction()
        ):
            raise ProfileValidationError(
                f"Source package output path already exists: {resolved_output_path}",
            )
        _publish_staging_directory(
            staging_root=staging_root,
            output_path=resolved_output_path,
        )

    return SourcePackageMaterializationResult(
        output_path=resolved_output_path,
        source_version=normalized_source_version,
        payload_files=payload_files,
        snapshot_manifest_path=_SOURCE_SNAPSHOT_MANIFEST_PATH.as_posix(),
    )


def _validate_delivery_profile(profile: DeploymentProfile) -> None:
    if profile.source_package.delivery_target is not SourcePackageDeliveryTarget.CUSTOMER:
        raise ProfileValidationError(
            f"Profile {profile.profile_id} is not a customer source-delivery profile.",
        )
    if not profile.installed_modules and not profile.source_package.allow_core_only_delivery:
        raise ProfileValidationError(
            f"Profile {profile.profile_id} cannot be materialized until it installs at least "
            "one connector module or explicitly allows a core-only delivery.",
        )


def _publish_staging_directory(*, staging_root: Path, output_path: Path) -> None:
    """Publish atomically, tolerating short Windows file-scanner locks."""

    for attempt in range(len(_WINDOWS_PUBLISH_RETRY_DELAYS_SECONDS) + 1):
        try:
            staging_root.rename(output_path)
            return
        except PermissionError as error:
            retryable = os.name == "nt" and getattr(error, "winerror", None) == 5
            if not retryable or attempt == len(_WINDOWS_PUBLISH_RETRY_DELAYS_SECONDS):
                raise ProfileValidationError(
                    f"Source package could not be published to: {output_path}",
                ) from error
            time.sleep(_WINDOWS_PUBLISH_RETRY_DELAYS_SECONDS[attempt])
        except OSError as error:
            raise ProfileValidationError(
                f"Source package could not be published to: {output_path}",
            ) from error


def _validate_materialization_inputs(
    *,
    repo_root: Path,
    profile: DeploymentProfile,
    manifest: ProfileManifest,
    snapshot: SourceSnapshotManifest,
) -> _ValidatedMaterializationInputs:
    profile_ids = {profile.profile_id, manifest.profile_id, snapshot.profile_id}
    if len(profile_ids) != 1:
        raise ProfileValidationError(
            "Source package profile, manifest, and snapshot ids must match.",
        )
    expected_manifest = generate_profile_manifest(profile)
    if (
        manifest_to_mapping(manifest) != manifest_to_mapping(expected_manifest)
        or manifest.source_package != expected_manifest.source_package
    ):
        raise ProfileValidationError(
            "Source package manifest does not match its deployment profile.",
        )
    expected_snapshot = build_source_snapshot_manifest(
        repo_root=repo_root,
        manifest=expected_manifest,
        profile=profile,
    )
    if (
        snapshot.files != expected_snapshot.files
        or snapshot.forbidden_terms != expected_snapshot.forbidden_terms
    ):
        raise ProfileValidationError(
            "Source package snapshot does not match the current profile allowlist and repository.",
        )
    validate_customer_scope_paths(
        profile=profile,
        source_files=expected_snapshot.files,
    )
    raise_for_source_snapshot_violations(snapshot)
    raise_for_source_snapshot_violations(expected_snapshot)
    return _ValidatedMaterializationInputs(
        manifest=expected_manifest,
        snapshot=expected_snapshot,
        source_hashes=source_file_hashes(
            repo_root=repo_root,
            source_files=expected_snapshot.files,
        ),
    )


def _write_generated_profile(*, staging_root: Path, profile: DeploymentProfile) -> None:
    resolved_staging_root = staging_root.resolve(strict=True)
    profile_path = (
        resolved_staging_root / "deployments" / profile.profile_id / "profile.yml"
    ).resolve(strict=False)
    if not profile_path.is_relative_to(resolved_staging_root):
        raise ProfileValidationError(
            f"Deployment profile path escapes the source-package staging directory: "
            f"{profile.profile_id}",
        )
    profile_path.parent.mkdir(parents=True, exist_ok=True)
    safe_dump = cast(Callable[..., str], import_module("yaml").safe_dump)
    content = safe_dump(
        dict(deployment_profile_to_mapping(profile, include_source_package=False)),
        allow_unicode=True,
        sort_keys=False,
    )
    profile_path.write_text(content, encoding="utf-8", newline="\n")


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"{json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False)}\n",
        encoding="utf-8",
        newline="\n",
    )


def _payload_file_paths(staging_root: Path) -> tuple[str, ...]:
    return tuple(
        sorted(
            path.relative_to(staging_root).as_posix()
            for path in staging_root.rglob("*")
            if path.is_file()
        ),
    )


def _source_snapshot_manifest_mapping(
    *,
    staging_root: Path,
    profile_id: str,
    payload_files: tuple[str, ...],
    source_version: str | None,
) -> Mapping[str, object]:
    payload: dict[str, object] = {
        "schema_version": 1,
        "profile_id": profile_id,
        "files": [
            {
                "path": relative_path,
                "sha256": _sha256(staging_root / relative_path),
            }
            for relative_path in payload_files
        ],
    }
    if source_version is not None:
        payload["source_version"] = source_version
    return payload


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source_file:
        for chunk in iter(lambda: source_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _scan_materialized_tree(*, staging_root: Path, manifest: ProfileManifest) -> None:
    materialized_manifest = replace(
        manifest,
        source_package=SourcePackageProfile(
            delivery_target=manifest.source_package.delivery_target,
            include_paths=("**/*",),
            forbidden_terms=manifest.source_package.forbidden_terms,
            allow_core_only_delivery=manifest.source_package.allow_core_only_delivery,
            overlay_path=manifest.source_package.overlay_path,
        ),
    )
    materialized_snapshot = build_source_snapshot_manifest(
        repo_root=staging_root,
        manifest=materialized_manifest,
    )
    raise_for_source_snapshot_violations(materialized_snapshot)
