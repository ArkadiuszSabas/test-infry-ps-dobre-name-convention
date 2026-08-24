"""System catalog definition use cases."""

from datetime import datetime
from uuid import UUID

from docmind_api.application.system_catalogs.commands import (
    SaveSystemCatalogDefinitionCommand,
    SaveSystemCatalogDisplayModeCommand,
    SaveSystemCatalogDisplayModePartCommand,
    SaveSystemCatalogExtensionFieldCommand,
    SystemCatalogDefinition,
    SystemCatalogNotFoundError,
    SystemCatalogValidationError,
)
from docmind_api.application.system_catalogs.definition_validation import (
    command_reuses_existing_id_with_new_code as _command_reuses_existing_id_with_new_code,
)
from docmind_api.application.system_catalogs.definition_validation import (
    display_part_extension_field_id as _display_part_extension_field_id,
)
from docmind_api.application.system_catalogs.definition_validation import (
    field_created_at as _field_created_at,
)
from docmind_api.application.system_catalogs.definition_validation import (
    field_id as _field_id,
)
from docmind_api.application.system_catalogs.definition_validation import (
    supported_system_catalog_key,
)
from docmind_api.application.system_catalogs.definition_validation import (
    validate_default_display_modes as _validate_default_display_modes,
)
from docmind_api.application.system_catalogs.field_validation import (
    validate_existing_field_value_shape as _validate_existing_field_value_shape,
)
from docmind_api.application.system_catalogs.field_validation import (
    validate_field_references as _validate_field_references,
)
from docmind_api.application.system_catalogs.field_validation import (
    validate_required_field_backfill as _validate_required_field_backfill,
)
from docmind_api.application.system_catalogs.ports import (
    Clock,
    SystemCatalogDefinitionRepository,
    SystemCatalogIdFactory,
)
from docmind_api.domain.system_catalogs.models import (
    DOCUMENT_TYPE_SYSTEM_CATALOG_KEY,
    SystemCatalogDisplayMode,
    SystemCatalogDisplayModePart,
    SystemCatalogExtensionField,
)

SUPPORTED_SYSTEM_CATALOG_KEYS = frozenset({DOCUMENT_TYPE_SYSTEM_CATALOG_KEY})

__all__ = (
    "SaveSystemCatalogDefinitionCommand",
    "SaveSystemCatalogDisplayModeCommand",
    "SaveSystemCatalogDisplayModePartCommand",
    "SaveSystemCatalogExtensionFieldCommand",
    "SystemCatalogDefinition",
    "SystemCatalogDefinitionService",
    "SystemCatalogNotFoundError",
    "SystemCatalogValidationError",
)


class SystemCatalogDefinitionService:
    """Application service for system catalog extension definitions."""

    def __init__(
        self,
        *,
        repository: SystemCatalogDefinitionRepository,
        clock: Clock,
        field_id_factory: SystemCatalogIdFactory,
        display_mode_id_factory: SystemCatalogIdFactory,
        display_part_id_factory: SystemCatalogIdFactory,
    ) -> None:
        self._repository = repository
        self._clock = clock
        self._field_id_factory = field_id_factory
        self._display_mode_id_factory = display_mode_id_factory
        self._display_part_id_factory = display_part_id_factory

    async def get_definition(self, system_catalog_key: str) -> SystemCatalogDefinition:
        """Return the current definition for a supported system catalog."""

        key = supported_system_catalog_key(system_catalog_key, SUPPORTED_SYSTEM_CATALOG_KEYS)
        fields, display_modes = await self._repository.get_definition(key)
        return SystemCatalogDefinition(
            system_catalog_key=key,
            fields=fields,
            display_modes=display_modes,
        )

    async def save_definition(
        self,
        command: SaveSystemCatalogDefinitionCommand,
    ) -> SystemCatalogDefinition:
        """Replace a supported system catalog definition."""

        key = supported_system_catalog_key(
            command.system_catalog_key,
            SUPPORTED_SYSTEM_CATALOG_KEYS,
        )
        existing_fields, existing_display_modes = await self._repository.get_definition(key)
        timestamp = self._clock.now()

        fields = await self._build_fields(
            key=key,
            commands=command.fields,
            existing_fields=existing_fields,
            timestamp=timestamp,
        )
        display_modes = self._build_display_modes(
            key=key,
            commands=command.display_modes,
            fields=fields,
            existing_display_modes=existing_display_modes,
            timestamp=timestamp,
        )
        _validate_default_display_modes(display_modes)

        saved_fields, saved_display_modes = await self._repository.replace_definition(
            system_catalog_key=key,
            fields=fields,
            display_modes=display_modes,
        )
        return SystemCatalogDefinition(
            system_catalog_key=key,
            fields=saved_fields,
            display_modes=saved_display_modes,
        )

    async def _build_fields(
        self,
        *,
        key: str,
        commands: tuple[SaveSystemCatalogExtensionFieldCommand, ...],
        existing_fields: tuple[SystemCatalogExtensionField, ...],
        timestamp: datetime,
    ) -> tuple[SystemCatalogExtensionField, ...]:
        existing_by_id = {UUID(str(field.id)): field for field in existing_fields}
        existing_by_code = {field.code: field for field in existing_fields}
        field_ids: set[UUID] = set()
        field_codes: set[str] = set()
        fields: list[SystemCatalogExtensionField] = []
        submitted_existing_ids: set[UUID] = set()

        for field_command in commands:
            try:
                candidate = SystemCatalogExtensionField(
                    id=_field_id(field_command, existing_by_id, existing_by_code)
                    or self._field_id_factory.new_id(),
                    system_catalog_key=key,
                    code=field_command.code,
                    label=field_command.label,
                    value_type=field_command.value_type,
                    dictionary_id=field_command.dictionary_id,
                    mapped_attribute_definition_id=field_command.mapped_attribute_definition_id,
                    is_required=field_command.is_required,
                    show_in_overview=field_command.show_in_overview,
                    field_order=field_command.field_order,
                    is_active=field_command.is_active,
                    created_at=_field_created_at(
                        field_command,
                        existing_by_id,
                        existing_by_code,
                        timestamp,
                    ),
                    updated_at=timestamp,
                )
            except ValueError as error:
                raise SystemCatalogValidationError(message=str(error)) from error

            if candidate.code in field_codes:
                raise SystemCatalogValidationError(
                    message="System catalog field codes must be unique.",
                    details={"code": candidate.code},
                )
            candidate_id = UUID(str(candidate.id))
            if candidate_id in field_ids:
                raise SystemCatalogValidationError(
                    message="System catalog field ids must be unique.",
                    details={"extension_field_id": str(candidate_id)},
                )
            if _command_reuses_existing_id_with_new_code(
                field_command,
                candidate,
                existing_by_id,
            ):
                raise SystemCatalogValidationError(
                    message="System catalog field code cannot be changed after creation.",
                    details={"extension_field_id": str(candidate.id)},
                )
            field_codes.add(candidate.code)
            field_ids.add(candidate_id)
            submitted_existing_ids.add(candidate_id)
            existing_field = existing_by_id.get(candidate_id)
            await _validate_field_references(
                self._repository,
                candidate,
                existing_field=existing_field,
            )
            if existing_field is not None:
                await _validate_existing_field_value_shape(
                    self._repository,
                    existing_field=existing_field,
                    candidate=candidate,
                )
            await _validate_required_field_backfill(
                self._repository,
                existing_field=existing_field,
                candidate=candidate,
            )
            fields.append(candidate)

        for existing_field in existing_fields:
            if UUID(str(existing_field.id)) in submitted_existing_ids:
                continue
            fields.append(
                SystemCatalogExtensionField(
                    id=existing_field.id,
                    system_catalog_key=existing_field.system_catalog_key,
                    code=existing_field.code,
                    label=existing_field.label,
                    value_type=existing_field.value_type,
                    dictionary_id=existing_field.dictionary_id,
                    mapped_attribute_definition_id=existing_field.mapped_attribute_definition_id,
                    is_required=existing_field.is_required,
                    show_in_overview=existing_field.show_in_overview,
                    field_order=existing_field.field_order,
                    is_active=False,
                    created_at=existing_field.created_at,
                    updated_at=timestamp,
                ),
            )

        return tuple(sorted(fields, key=lambda field: (field.field_order, field.label, field.code)))

    def _build_display_modes(
        self,
        *,
        key: str,
        commands: tuple[SaveSystemCatalogDisplayModeCommand, ...],
        fields: tuple[SystemCatalogExtensionField, ...],
        existing_display_modes: tuple[SystemCatalogDisplayMode, ...],
        timestamp: datetime,
    ) -> tuple[SystemCatalogDisplayMode, ...]:
        existing_by_id = {UUID(str(mode.id)): mode for mode in existing_display_modes}
        existing_by_name = {mode.name: mode for mode in existing_display_modes}
        active_fields_by_id = {UUID(str(field.id)): field for field in fields if field.is_active}
        active_fields_by_code = {field.code: field for field in fields if field.is_active}
        mode_ids: set[UUID] = set()
        mode_names: set[str] = set()
        part_ids: set[UUID] = set()
        modes: list[SystemCatalogDisplayMode] = []

        for mode_command in commands:
            mode_id, existing_mode = self._display_mode_identity(
                command=mode_command,
                existing_by_id=existing_by_id,
                existing_by_name=existing_by_name,
            )
            if mode_id in mode_ids:
                raise SystemCatalogValidationError(
                    message="System catalog display mode ids must be unique.",
                    details={"display_mode_id": str(mode_id)},
                )
            parts = self._build_display_mode_parts(
                mode_id=mode_id,
                commands=mode_command.parts,
                active_fields_by_id=active_fields_by_id,
                active_fields_by_code=active_fields_by_code,
                submitted_part_ids=part_ids,
            )
            if mode_command.is_active and not parts:
                raise SystemCatalogValidationError(
                    message="Active display modes require at least one part.",
                    details={"display_mode_id": str(mode_id)},
                )
            try:
                modes.append(
                    SystemCatalogDisplayMode(
                        id=mode_id,
                        system_catalog_key=key,
                        name=mode_command.name,
                        is_default=mode_command.is_default,
                        is_active=mode_command.is_active,
                        created_at=existing_mode.created_at
                        if existing_mode is not None
                        else timestamp,
                        updated_at=timestamp,
                        parts=parts,
                    ),
                )
            except ValueError as error:
                raise SystemCatalogValidationError(message=str(error)) from error
            mode = modes[-1]
            if mode.name in mode_names:
                raise SystemCatalogValidationError(
                    message="System catalog display mode names must be unique.",
                    details={"name": mode.name},
                )
            mode_ids.add(mode_id)
            mode_names.add(mode.name)

        return tuple(modes)

    def _display_mode_identity(
        self,
        *,
        command: SaveSystemCatalogDisplayModeCommand,
        existing_by_id: dict[UUID, SystemCatalogDisplayMode],
        existing_by_name: dict[str, SystemCatalogDisplayMode],
    ) -> tuple[UUID, SystemCatalogDisplayMode | None]:
        if command.id is not None:
            mode_id = UUID(str(command.id))
            return mode_id, existing_by_id.get(mode_id)
        existing_mode = existing_by_name.get(command.name.strip())
        if existing_mode is not None:
            return UUID(str(existing_mode.id)), existing_mode
        return self._display_mode_id_factory.new_id(), None

    def _build_display_mode_parts(
        self,
        *,
        mode_id: UUID,
        commands: tuple[SaveSystemCatalogDisplayModePartCommand, ...],
        active_fields_by_id: dict[UUID, SystemCatalogExtensionField],
        active_fields_by_code: dict[str, SystemCatalogExtensionField],
        submitted_part_ids: set[UUID],
    ) -> tuple[SystemCatalogDisplayModePart, ...]:
        part_orders: set[int] = set()
        parts: list[SystemCatalogDisplayModePart] = []
        for part_command in commands:
            extension_field_id = _display_part_extension_field_id(
                part_command,
                active_fields_by_id,
                active_fields_by_code,
            )
            try:
                part = SystemCatalogDisplayModePart(
                    id=(
                        UUID(str(part_command.id))
                        if part_command.id is not None
                        else self._display_part_id_factory.new_id()
                    ),
                    display_mode_id=mode_id,
                    part_order=part_command.part_order,
                    source_type=part_command.source_type,
                    extension_field_id=extension_field_id,
                    separator_before=part_command.separator_before,
                )
            except ValueError as error:
                raise SystemCatalogValidationError(message=str(error)) from error
            part_id = UUID(str(part.id))
            if part_id in submitted_part_ids:
                raise SystemCatalogValidationError(
                    message="System catalog display mode part ids must be unique.",
                    details={"display_mode_part_id": str(part_id)},
                )
            if part.part_order in part_orders:
                raise SystemCatalogValidationError(
                    message="Display mode part order must be unique within a mode.",
                    details={"part_order": part.part_order},
                )
            part_orders.add(part.part_order)
            submitted_part_ids.add(part_id)
            parts.append(part)

        return tuple(sorted(parts, key=lambda part: part.part_order))
