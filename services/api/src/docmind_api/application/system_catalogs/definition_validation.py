"""Validation helpers for system catalog definition saves."""

from datetime import datetime
from uuid import UUID

from docmind_api.application.system_catalogs.commands import (
    SaveSystemCatalogDisplayModePartCommand,
    SaveSystemCatalogExtensionFieldCommand,
    SystemCatalogNotFoundError,
    SystemCatalogValidationError,
)
from docmind_api.domain.system_catalogs.models import (
    SystemCatalogDisplayMode,
    SystemCatalogDisplayPartSourceType,
    SystemCatalogExtensionField,
    normalize_system_catalog_key,
)


def supported_system_catalog_key(
    system_catalog_key: str,
    supported_keys: frozenset[str],
) -> str:
    """Validate and return a supported system catalog key."""

    try:
        key = normalize_system_catalog_key(system_catalog_key)
    except ValueError as error:
        raise SystemCatalogValidationError(message=str(error)) from error
    if key not in supported_keys:
        raise SystemCatalogNotFoundError(system_catalog_key=key)
    return key


def field_id(
    command: SaveSystemCatalogExtensionFieldCommand,
    existing_by_id: dict[UUID, SystemCatalogExtensionField],
    existing_by_code: dict[str, SystemCatalogExtensionField],
) -> UUID | None:
    """Resolve the row id for a submitted field command."""

    existing_for_code = existing_by_code.get(command.code.strip())
    if command.id is not None:
        command_id = UUID(str(command.id))
        if existing_for_code is not None and UUID(str(existing_for_code.id)) != command_id:
            raise SystemCatalogValidationError(
                message="System catalog field id does not match the existing field code.",
                details={
                    "extension_field_id": str(command_id),
                    "code": command.code.strip(),
                },
            )
        return command_id
    if existing_for_code is not None:
        return UUID(str(existing_for_code.id))
    return None


def command_reuses_existing_id_with_new_code(
    command: SaveSystemCatalogExtensionFieldCommand,
    candidate: SystemCatalogExtensionField,
    existing_by_id: dict[UUID, SystemCatalogExtensionField],
) -> bool:
    """Return whether a command tries to rename an existing field code."""

    if command.id is None:
        return False
    existing = existing_by_id.get(UUID(str(command.id)))
    return existing is not None and existing.code != candidate.code


def field_created_at(
    command: SaveSystemCatalogExtensionFieldCommand,
    existing_by_id: dict[UUID, SystemCatalogExtensionField],
    existing_by_code: dict[str, SystemCatalogExtensionField],
    timestamp: datetime,
) -> datetime:
    """Resolve the created_at timestamp for a field save."""

    if command.id is not None:
        existing = existing_by_id.get(UUID(str(command.id)))
        if existing is not None:
            return existing.created_at
    existing = existing_by_code.get(command.code.strip())
    if existing is not None:
        return existing.created_at
    return timestamp


def display_part_extension_field_id(
    command: SaveSystemCatalogDisplayModePartCommand,
    active_fields_by_id: dict[UUID, SystemCatalogExtensionField],
    active_fields_by_code: dict[str, SystemCatalogExtensionField],
) -> UUID | None:
    """Resolve the referenced extension field id for one display mode part."""

    if command.source_type == SystemCatalogDisplayPartSourceType.BASE_NAME:
        if command.extension_field_id is not None or command.extension_field_code is not None:
            raise SystemCatalogValidationError(
                message="Base-name display parts cannot reference extension fields.",
            )
        return None

    field_id = _display_part_extension_field_id_by_id(
        command.extension_field_id,
        active_fields_by_id,
    )
    field_id_by_code = _display_part_extension_field_id_by_code(
        command.extension_field_code,
        active_fields_by_code,
    )
    if field_id is not None and field_id_by_code is not None and field_id != field_id_by_code:
        raise SystemCatalogValidationError(
            message="Display mode extension field id and code must reference the same field.",
            details={
                "extension_field_id": str(field_id),
                "extension_field_code": command.extension_field_code,
            },
        )
    resolved_field_id = field_id or field_id_by_code
    if resolved_field_id is None:
        raise SystemCatalogValidationError(
            message=(
                "Extension-field display parts require extension_field_id or extension_field_code."
            ),
        )
    return resolved_field_id


def _display_part_extension_field_id_by_id(
    extension_field_id: UUID | str | None,
    active_fields_by_id: dict[UUID, SystemCatalogExtensionField],
) -> UUID | None:
    if extension_field_id is not None:
        referenced_field_id = UUID(str(extension_field_id))
        if referenced_field_id not in active_fields_by_id:
            raise SystemCatalogValidationError(
                message="Display mode cannot reference an inactive or missing extension field.",
                details={"extension_field_id": str(referenced_field_id)},
            )
        return referenced_field_id
    return None


def _display_part_extension_field_id_by_code(
    extension_field_code: str | None,
    active_fields_by_code: dict[str, SystemCatalogExtensionField],
) -> UUID | None:
    if extension_field_code is not None:
        field = active_fields_by_code.get(extension_field_code.strip())
        if field is None:
            raise SystemCatalogValidationError(
                message="Display mode cannot reference an inactive or missing extension field.",
                details={"extension_field_code": extension_field_code},
            )
        return UUID(str(field.id))
    return None


def validate_default_display_modes(display_modes: tuple[SystemCatalogDisplayMode, ...]) -> None:
    """Ensure at most one active display mode is default."""

    default_modes = tuple(mode for mode in display_modes if mode.is_active and mode.is_default)
    if len(default_modes) > 1:
        raise SystemCatalogValidationError(
            message="Only one active default display mode is allowed per system catalog.",
        )


def optional_uuid(value: UUID | str | None) -> UUID | None:
    """Normalize an optional UUID-like value."""

    if value is None:
        return None
    return UUID(str(value))
