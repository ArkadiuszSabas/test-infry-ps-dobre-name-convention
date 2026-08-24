"""SQL row mappers for system catalog persistence."""

from collections.abc import Mapping
from typing import Any

from docmind_api.domain.system_catalogs.models import (
    SystemCatalogDisplayMode,
    SystemCatalogDisplayModePart,
    SystemCatalogDisplayPartSourceType,
    SystemCatalogExtensionField,
    SystemCatalogExtensionValueType,
)


def field_from_row(row: Mapping[Any, Any]) -> SystemCatalogExtensionField:
    """Map one extension field row."""

    return SystemCatalogExtensionField(
        id=row["id"],
        system_catalog_key=row["system_catalog_key"],
        code=row["code"],
        label=row["label"],
        value_type=SystemCatalogExtensionValueType(row["value_type"]),
        dictionary_id=row["dictionary_id"],
        mapped_attribute_definition_id=row["mapped_attribute_definition_id"],
        is_required=row["is_required"],
        show_in_overview=row["show_in_overview"],
        field_order=row["field_order"],
        is_active=row["is_active"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def display_mode_from_row(
    row: Mapping[Any, Any],
    *,
    parts: tuple[SystemCatalogDisplayModePart, ...],
) -> SystemCatalogDisplayMode:
    """Map one display mode row."""

    return SystemCatalogDisplayMode(
        id=row["id"],
        system_catalog_key=row["system_catalog_key"],
        name=row["name"],
        is_default=row["is_default"],
        is_active=row["is_active"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        parts=parts,
    )


def display_mode_part_from_row(row: Mapping[Any, Any]) -> SystemCatalogDisplayModePart:
    """Map one display mode part row."""

    return SystemCatalogDisplayModePart(
        id=row["id"],
        display_mode_id=row["display_mode_id"],
        part_order=row["part_order"],
        source_type=SystemCatalogDisplayPartSourceType(row["source_type"]),
        extension_field_id=row["extension_field_id"],
        separator_before=row["separator_before"],
    )
