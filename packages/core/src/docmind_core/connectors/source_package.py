"""Minimal source-package manifest and forbidden scan gate."""

from __future__ import annotations

import json
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from importlib.util import find_spec
from pathlib import Path

from docmind_core.connectors.profiles import (
    DeploymentProfile,
    ProfileManifest,
    ProfileValidationError,
    manifest_to_mapping,
)


@dataclass(frozen=True, slots=True)
class SourcePackageScanViolation:
    """Forbidden connector term found in an allowlisted source snapshot file."""

    path: str
    term: str
    location: str


@dataclass(frozen=True, slots=True)
class SourceSnapshotManifest:
    """Deterministic simulated source snapshot manifest."""

    profile_id: str
    files: tuple[str, ...]
    metadata_files: tuple[str, ...]
    forbidden_terms: tuple[str, ...]
    violations: tuple[SourcePackageScanViolation, ...]

    @property
    def is_valid(self) -> bool:
        """Return whether the snapshot passed the deny scan."""

        return not self.violations


def build_source_snapshot_manifest(
    *,
    repo_root: Path,
    manifest: ProfileManifest,
    profile: DeploymentProfile | None = None,
) -> SourceSnapshotManifest:
    """Build and scan a simulated allowlisted source snapshot."""

    include_paths = manifest.source_package.include_paths
    forbidden_terms = manifest.source_package.forbidden_terms
    if not include_paths:
        raise ProfileValidationError(
            f"Profile {manifest.profile_id} must define source_package.include_paths.",
        )

    files = _expand_include_paths(repo_root=repo_root, include_paths=include_paths)
    if profile is not None:
        _validate_installed_module_source_coverage(
            repo_root=repo_root,
            files=files,
            profile=profile,
        )
    _validate_declared_asset_coverage(
        repo_root=repo_root,
        files=files,
        manifest=manifest,
    )
    metadata_entries = _metadata_scan_entries(
        manifest=manifest,
        files=files,
        profile=profile,
    )
    violations = (
        *_scan_files(
            repo_root=repo_root,
            files=files,
            forbidden_terms=forbidden_terms,
        ),
        *_scan_metadata_entries(
            entries=metadata_entries,
            forbidden_terms=forbidden_terms,
        ),
    )
    return SourceSnapshotManifest(
        profile_id=manifest.profile_id,
        files=tuple(str(path.as_posix()) for path in files),
        metadata_files=tuple(entry.path for entry in metadata_entries),
        forbidden_terms=forbidden_terms,
        violations=violations,
    )


@dataclass(frozen=True, slots=True)
class _MetadataScanEntry:
    path: str
    content: str


def _metadata_scan_entries(
    *,
    manifest: ProfileManifest,
    files: tuple[Path, ...],
    profile: DeploymentProfile | None,
) -> tuple[_MetadataScanEntry, ...]:
    entries: list[_MetadataScanEntry] = [
        _MetadataScanEntry(
            path="generated/profile-manifest.json",
            content=json.dumps(manifest_to_mapping(manifest), sort_keys=True),
        ),
        _MetadataScanEntry(
            path="generated/source-snapshot-manifest.json",
            content=json.dumps(
                {
                    "profile_id": manifest.profile_id,
                    "files": [path.as_posix() for path in files],
                },
                sort_keys=True,
            ),
        ),
    ]
    if profile is not None:
        entries.append(
            _MetadataScanEntry(
                path="generated/profile-input-metadata.json",
                content=json.dumps(_profile_to_scan_mapping(profile), sort_keys=True),
            ),
        )
    return tuple(entries)


def _profile_to_scan_mapping(profile: DeploymentProfile) -> Mapping[str, object]:
    """Return profile metadata that may be delivered, excluding the deny-list itself."""

    return {
        "schema_version": profile.schema_version,
        "profile_id": profile.profile_id,
        "display_name": profile.display_name,
        "installed_modules": [
            {
                "module_id": item.module_id,
                "connector_folder": item.connector_folder,
                "import_path": item.import_path,
                "api_router_entrypoint": item.api_router_entrypoint,
                "approved_document_handler_entrypoint": (item.approved_document_handler_entrypoint),
                "document_deletion_handler_entrypoint": (item.document_deletion_handler_entrypoint),
                "api_route_prefixes": list(item.api_route_prefixes),
                "worker_hook_ids": list(item.worker_hook_ids),
                "migration_bundle_ids": list(item.migration_bundle_ids),
                "ui_extension_ids": list(item.ui_extension_ids),
            }
            for item in profile.installed_modules
        ],
        "source_package": {
            "delivery_target": profile.source_package.delivery_target.value,
            "include_paths": list(profile.source_package.include_paths),
            "allow_core_only_delivery": profile.source_package.allow_core_only_delivery,
            "overlay_path": profile.source_package.overlay_path,
        },
    }


def _validate_installed_module_source_coverage(
    *,
    repo_root: Path,
    files: tuple[Path, ...],
    profile: DeploymentProfile,
) -> None:
    for module_entry in profile.installed_modules:
        module_source_path = _entrypoint_source_path(
            repo_root=repo_root,
            import_path=module_entry.import_path,
        )
        if not _path_is_in_snapshot(module_source_path, files=files):
            raise ProfileValidationError(
                f"Installed module {module_entry.module_id} source is not included in the "
                f"source snapshot: {module_source_path.as_posix()}.",
            )
        if module_entry.api_router_entrypoint is not None:
            router_source_path = _entrypoint_source_path(
                repo_root=repo_root,
                import_path=module_entry.api_router_entrypoint,
            )
            if not _path_is_in_snapshot(router_source_path, files=files):
                raise ProfileValidationError(
                    f"Installed module {module_entry.module_id} API router entrypoint source "
                    f"is not included in the source snapshot: {router_source_path.as_posix()}.",
                )
        if module_entry.approved_document_handler_entrypoint is not None:
            handler_source_path = _entrypoint_source_path(
                repo_root=repo_root,
                import_path=module_entry.approved_document_handler_entrypoint,
            )
            if not _path_is_in_snapshot(handler_source_path, files=files):
                raise ProfileValidationError(
                    f"Installed module {module_entry.module_id} approved document handler "
                    f"source is not included in the source snapshot: "
                    f"{handler_source_path.as_posix()}.",
                )
        if module_entry.document_deletion_handler_entrypoint is not None:
            handler_source_path = _entrypoint_source_path(
                repo_root=repo_root,
                import_path=module_entry.document_deletion_handler_entrypoint,
            )
            if not _path_is_in_snapshot(handler_source_path, files=files):
                raise ProfileValidationError(
                    f"Installed module {module_entry.module_id} document deletion handler "
                    f"source is not included in the source snapshot: "
                    f"{handler_source_path.as_posix()}.",
                )

        connector_folder = repo_root / "packages" / "connectors" / module_entry.connector_folder
        if connector_folder.exists() and not _directory_has_snapshot_files(
            connector_folder.relative_to(repo_root),
            files=files,
        ):
            raise ProfileValidationError(
                f"Installed module {module_entry.module_id} connector folder is not included "
                f"in the source snapshot: {module_entry.connector_folder}.",
            )


def _entrypoint_source_path(*, repo_root: Path, import_path: str) -> Path:
    module_name, _separator, _function_name = import_path.partition(":")
    spec = find_spec(module_name)
    if spec is None or spec.origin is None:
        raise ProfileValidationError(
            f"Installed module import path cannot be resolved: {import_path}."
        )

    origin = Path(spec.origin).resolve()
    try:
        return origin.relative_to(repo_root)
    except ValueError as error:
        raise ProfileValidationError(
            f"Installed module import path is outside the repository source tree: {import_path}.",
        ) from error


def _validate_declared_asset_coverage(
    *,
    repo_root: Path,
    files: tuple[Path, ...],
    manifest: ProfileManifest,
) -> None:
    module_by_id = {module.module_id: module for module in manifest.installed_modules}
    for ui_extension in manifest.ui_extensions:
        ui_path = Path(ui_extension.module_path)
        if not _path_is_in_snapshot(ui_path, files=files):
            raise ProfileValidationError(
                f"UI extension {ui_extension.id} source is not included in the source "
                f"snapshot: {ui_extension.module_path}.",
            )
    for bundle in manifest.migration_bundles:
        module = module_by_id[bundle.module_id]
        bundle_path = Path("packages") / "connectors" / module.connector_folder / bundle.path
        absolute_bundle_path = repo_root / bundle_path
        if absolute_bundle_path.exists() and not _directory_has_snapshot_files(
            bundle_path,
            files=files,
        ):
            raise ProfileValidationError(
                f"Migration bundle {bundle.id} is not included in the source snapshot: "
                f"{bundle_path.as_posix()}.",
            )


def _path_is_in_snapshot(path: Path, *, files: tuple[Path, ...]) -> bool:
    normalized = Path(path.as_posix().strip("/"))
    return normalized in files


def _directory_has_snapshot_files(path: Path, *, files: tuple[Path, ...]) -> bool:
    normalized = path.as_posix().strip("/")
    return any(file.as_posix().startswith(f"{normalized}/") for file in files)


def _scan_metadata_entries(
    *,
    entries: tuple[_MetadataScanEntry, ...],
    forbidden_terms: tuple[str, ...],
) -> tuple[SourcePackageScanViolation, ...]:
    violations: list[SourcePackageScanViolation] = []
    normalized_terms = _normalized_terms(forbidden_terms)
    for entry in entries:
        normalized_path = _normalize_for_scan(entry.path)
        for raw_term, normalized_term in normalized_terms:
            if normalized_term and normalized_term in normalized_path:
                violations.append(
                    SourcePackageScanViolation(
                        path=entry.path,
                        term=raw_term,
                        location="path",
                    ),
                )
        for line_number, line in enumerate(entry.content.splitlines(), start=1):
            normalized_line = _normalize_for_scan(line)
            for raw_term, normalized_term in normalized_terms:
                if normalized_term and normalized_term in normalized_line:
                    violations.append(
                        SourcePackageScanViolation(
                            path=entry.path,
                            term=raw_term,
                            location=f"line {line_number}",
                        ),
                    )
    return tuple(violations)


def _normalized_terms(forbidden_terms: tuple[str, ...]) -> tuple[tuple[str, str], ...]:
    return tuple((term, _normalize_for_scan(term)) for term in forbidden_terms if term)


def _normalize_for_scan(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.casefold())
    return "".join(character for character in normalized if not unicodedata.combining(character))


def _scan_files(
    *,
    repo_root: Path,
    files: tuple[Path, ...],
    forbidden_terms: tuple[str, ...],
) -> tuple[SourcePackageScanViolation, ...]:
    violations: list[SourcePackageScanViolation] = []
    normalized_terms = _normalized_terms(forbidden_terms)
    for relative_path in files:
        path_text = relative_path.as_posix()
        normalized_path = _normalize_for_scan(path_text)
        for raw_term, normalized_term in normalized_terms:
            if normalized_term and normalized_term in normalized_path:
                violations.append(
                    SourcePackageScanViolation(
                        path=path_text,
                        term=raw_term,
                        location="path",
                    ),
                )
        content = (repo_root / relative_path).read_text(encoding="utf-8", errors="ignore")
        for line_number, line in enumerate(content.splitlines(), start=1):
            normalized_line = _normalize_for_scan(line)
            for raw_term, normalized_term in normalized_terms:
                if normalized_term and normalized_term in normalized_line:
                    violations.append(
                        SourcePackageScanViolation(
                            path=path_text,
                            term=raw_term,
                            location=f"line {line_number}",
                        ),
                    )
    return tuple(violations)


def _expand_include_paths(*, repo_root: Path, include_paths: tuple[str, ...]) -> tuple[Path, ...]:
    files: set[Path] = set()
    for include_path in include_paths:
        normalized = include_path.replace("\\", "/").strip("/")
        if not normalized or normalized.startswith("../") or "/../" in normalized:
            raise ProfileValidationError(
                f"source_package.include_paths contains an unsafe path: {include_path}",
            )
        matches = repo_root.glob(normalized)
        for match in matches:
            if match.is_file() and _is_source_snapshot_file(match):
                files.add(match.relative_to(repo_root))
            elif match.is_dir():
                files.update(
                    child.relative_to(repo_root)
                    for child in match.rglob("*")
                    if child.is_file() and _is_source_snapshot_file(child)
                )
    if not files:
        raise ProfileValidationError("source_package.include_paths did not match any files.")
    return tuple(sorted(files, key=lambda path: path.as_posix()))


def _is_source_snapshot_file(path: Path) -> bool:
    if path.suffix in {".pyc", ".pyo"}:
        return False
    return "__pycache__" not in path.parts


def raise_for_source_snapshot_violations(snapshot: SourceSnapshotManifest) -> None:
    """Raise a profile validation error when a snapshot leaked forbidden terms."""

    if snapshot.is_valid:
        return

    details = ", ".join(
        f"{violation.path}:{violation.location}:{violation.term}"
        for violation in snapshot.violations
    )
    raise ProfileValidationError(
        f"Source package scan failed for profile {snapshot.profile_id}: {details}",
    )
