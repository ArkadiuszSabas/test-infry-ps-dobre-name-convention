"""CLI for the minimal connector source-package validation gate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from docmind_connectors.registry import available_connector_modules
from docmind_core.connectors.profiles import (
    ProfileValidationError,
    generate_profile_manifest,
    load_deployment_profile,
    manifest_to_mapping,
)
from docmind_core.connectors.source_package import (
    build_source_snapshot_manifest,
    raise_for_source_snapshot_violations,
)
from docmind_core.connectors.source_package_materialization import (
    materialize_source_package,
)


def main() -> None:
    """Run the source-package validation command."""

    parser = argparse.ArgumentParser(
        description="Validate a DocMind connector deployment profile source package.",
    )
    parser.add_argument(
        "profile",
        help="Profile id under deployments/<profile>/profile.yml, or a profile.yml path.",
    )
    parser.add_argument(
        "--repo-root",
        default=None,
        help="Repository root. Defaults to the current working directory.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Materialize a customer source snapshot in a new directory.",
    )
    parser.add_argument(
        "--source-version",
        default=None,
        help="Optional source revision recorded in the snapshot manifest.",
    )
    args = parser.parse_args()

    repo_root = Path(args.repo_root or Path.cwd()).resolve()
    profile_path = _resolve_profile_path(repo_root=repo_root, profile=args.profile)
    try:
        profile = load_deployment_profile(profile_path)
        manifest = generate_profile_manifest(
            profile,
            available_modules=available_connector_modules(),
        )
        snapshot = build_source_snapshot_manifest(
            repo_root=repo_root,
            manifest=manifest,
            profile=profile,
        )
        raise_for_source_snapshot_violations(snapshot)
    except ProfileValidationError as error:
        raise SystemExit(str(error)) from error

    summary: dict[str, object] = {
        "profile_id": manifest.profile_id,
        "manifest": manifest_to_mapping(manifest),
        "source_snapshot": {
            "file_count": len(snapshot.files),
            "metadata_file_count": len(snapshot.metadata_files),
            "violations": list[str](),
        },
    }
    if args.output_dir is not None:
        try:
            validate_materialization_profile_path(
                repo_root=repo_root,
                profile_path=profile_path,
                profile_id=profile.profile_id,
            )
        except ProfileValidationError as error:
            raise SystemExit(str(error)) from error
        output_path = Path(args.output_dir)
        if not output_path.is_absolute():
            output_path = repo_root / output_path
        try:
            materialization = materialize_source_package(
                repo_root=repo_root,
                output_path=output_path,
                profile=profile,
                manifest=manifest,
                snapshot=snapshot,
                source_version=args.source_version,
            )
        except ProfileValidationError as error:
            raise SystemExit(str(error)) from error
        summary["materialization"] = {
            "output_path": str(materialization.output_path),
            "payload_file_count": len(materialization.payload_files),
            "snapshot_manifest_path": materialization.snapshot_manifest_path,
            "source_version": materialization.source_version,
        }
    print(json.dumps(summary, indent=2, sort_keys=True))


def _resolve_profile_path(*, repo_root: Path, profile: str) -> Path:
    profile_path = Path(profile)
    if profile_path.suffix in {".yml", ".yaml"}:
        return profile_path if profile_path.is_absolute() else repo_root / profile_path

    return repo_root / "deployments" / profile / "profile.yml"


def validate_materialization_profile_path(
    *,
    repo_root: Path,
    profile_path: Path,
    profile_id: str,
) -> None:
    """Require materialization to use the repository's reviewed profile file."""

    expected_path = repo_root / "deployments" / profile_id / "profile.yml"
    try:
        resolved_profile_path = profile_path.resolve(strict=True)
        resolved_expected_path = expected_path.resolve(strict=True)
    except OSError as error:
        raise ProfileValidationError(
            f"Reviewed deployment profile does not exist: {expected_path}",
        ) from error
    if resolved_profile_path != resolved_expected_path:
        raise ProfileValidationError(
            "Customer source materialization requires the reviewed repository profile at "
            f"deployments/{profile_id}/profile.yml.",
        )


if __name__ == "__main__":
    main()
