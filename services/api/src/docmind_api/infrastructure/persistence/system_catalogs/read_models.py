"""Document type read-model composition for system catalog extensions."""

from uuid import UUID

from docmind_api.application.document_types.ports import (
    DocumentTypeExtensionValueReadModel,
    DocumentTypeOverviewParameter,
    DocumentTypeReadModel,
)
from docmind_api.domain.document_types.models import DocumentType
from docmind_api.domain.system_catalogs.models import (
    SystemCatalogDisplayMode,
    SystemCatalogDisplayModePart,
    SystemCatalogDisplayPartSourceType,
    SystemCatalogExtensionField,
)


class StoredExtensionValue:
    """Stored extension value joined with its display label."""

    def __init__(
        self,
        *,
        dictionary_entry_id: UUID | None,
        text_value: str | None,
        display_value: str | None,
    ) -> None:
        self.dictionary_entry_id = dictionary_entry_id
        self.text_value = text_value
        self.display_value = display_value


def build_document_type_read_model(
    *,
    document_type: DocumentType,
    fields: tuple[SystemCatalogExtensionField, ...],
    values: dict[UUID, StoredExtensionValue],
    display_mode: SystemCatalogDisplayMode | None,
) -> DocumentTypeReadModel:
    """Build one enriched document type read model."""

    extension_values = tuple(
        _extension_value_read_model(field=field, value=values.get(UUID(str(field.id))))
        for field in fields
    )
    parameters = tuple(
        DocumentTypeOverviewParameter(
            code=value.code,
            label=value.label,
            value=value.display_value,
        )
        for value in extension_values
        if value.show_in_overview
    )
    display_label, sort_key = _display_label_and_sort_key(
        document_type=document_type,
        values_by_field_id={
            value.extension_field_id: value.display_value for value in extension_values
        },
        display_mode=display_mode,
    )
    return DocumentTypeReadModel(
        document_type=document_type,
        display_label=display_label,
        extension_values=extension_values,
        parameters=parameters,
        display_mode_id=UUID(str(display_mode.id)) if display_mode is not None else None,
        sort_key=sort_key,
    )


def _extension_value_read_model(
    *,
    field: SystemCatalogExtensionField,
    value: StoredExtensionValue | None,
) -> DocumentTypeExtensionValueReadModel:
    return DocumentTypeExtensionValueReadModel(
        extension_field_id=UUID(str(field.id)),
        code=field.code,
        label=field.label,
        value_type=field.value_type,
        dictionary_id=UUID(str(field.dictionary_id)) if field.dictionary_id is not None else None,
        dictionary_entry_id=value.dictionary_entry_id if value is not None else None,
        text_value=value.text_value if value is not None else None,
        display_value=value.display_value if value is not None else None,
        show_in_overview=field.show_in_overview,
        field_order=field.field_order,
    )


def _display_label_and_sort_key(
    *,
    document_type: DocumentType,
    values_by_field_id: dict[UUID, str | None],
    display_mode: SystemCatalogDisplayMode | None,
) -> tuple[str, tuple[str, ...]]:
    if display_mode is None:
        return document_type.name, (document_type.name.casefold(),)

    label_parts: list[str] = []
    sort_parts: list[str] = []
    for part in display_mode.parts:
        value = _display_part_value(
            document_type=document_type,
            values_by_field_id=values_by_field_id,
            part=part,
        )
        sort_parts.append((value or "").casefold())
        if not value:
            continue
        if label_parts and part.separator_before is not None:
            label_parts.append(part.separator_before)
        label_parts.append(value)

    label = "".join(label_parts).strip()
    if not label:
        return document_type.name, (document_type.name.casefold(), *sort_parts)
    return label, tuple(sort_parts)


def _display_part_value(
    *,
    document_type: DocumentType,
    values_by_field_id: dict[UUID, str | None],
    part: SystemCatalogDisplayModePart,
) -> str | None:
    if part.source_type == SystemCatalogDisplayPartSourceType.BASE_NAME:
        return document_type.name
    if part.extension_field_id is None:
        return None
    return values_by_field_id.get(UUID(str(part.extension_field_id)))
