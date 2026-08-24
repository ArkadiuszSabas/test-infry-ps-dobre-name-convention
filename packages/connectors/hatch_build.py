"""Build profile-selected connector packages from connector-owned source roots."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from hatchling.builders.hooks.plugin.interface import BuildHookInterface
from hatchling.builders.wheel import WheelBuilderConfig

_CONNECTOR_NAMESPACE_ROOT = Path("src") / "docmind_connectors"


class CustomBuildHook(BuildHookInterface[WheelBuilderConfig]):
    """Merge connector-owned Python packages into the shared connector wheel."""

    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        """Include every connector package physically present in the source tree."""

        force_include = build_data["force_include"]
        dev_mode_dirs = self.build_config.dev_mode_dirs

        for package_path in _discover_connector_packages(Path(self.root)):
            if version != "editable":
                distribution_path = f"docmind_connectors/{package_path.name}"
                force_include[str(package_path)] = distribution_path

            connector_source_root = package_path.parents[1]
            relative_source_root = connector_source_root.relative_to(self.root).as_posix()
            if relative_source_root not in dev_mode_dirs:
                dev_mode_dirs.append(relative_source_root)


def _discover_connector_packages(project_root: Path) -> tuple[Path, ...]:
    """Return import packages owned by immediate connector folders."""

    packages_by_name: dict[str, Path] = {}
    for connector_root in sorted(project_root.iterdir(), key=lambda path: path.name):
        namespace_root = connector_root / _CONNECTOR_NAMESPACE_ROOT
        if not namespace_root.is_dir():
            continue

        for package_path in sorted(namespace_root.iterdir(), key=lambda path: path.name):
            if not package_path.is_dir() or not (package_path / "__init__.py").is_file():
                continue

            previous_path = packages_by_name.get(package_path.name)
            if previous_path is not None:
                raise ValueError(
                    "Connector Python package names must be unique: "
                    f"{previous_path} and {package_path}."
                )
            packages_by_name[package_path.name] = package_path

    return tuple(packages_by_name.values())
