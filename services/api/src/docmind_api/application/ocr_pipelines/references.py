"""Reference extraction helpers for OCR pipeline step config."""

from collections.abc import Mapping
from dataclasses import dataclass

from docmind_api.application.ocr_pipelines.json_helpers import object_mapping, object_sequence

NORMALIZATION_IMPLEMENTATION_ID = "document.normalization.fields"
REFERENCE_VALIDATED_IMPLEMENTATION_IDS = frozenset({NORMALIZATION_IMPLEMENTATION_ID})


@dataclass(frozen=True, slots=True)
class AttributeReference:
    """Attribute reference plus its diagnostic path."""

    value: str
    path: str


def document_type_reference(config: Mapping[str, object]) -> str | None:
    """Return a document type reference from supported block config when present."""

    for key in ("document_type_id", "document_type_external_id"):
        value = config.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def attribute_references(
    config: Mapping[str, object],
    *,
    path: str,
) -> tuple[AttributeReference, ...]:
    """Return attribute references from supported schema-aware block config shapes."""

    references: list[AttributeReference] = []
    for key in ("attributes", "field_mappings"):
        values = object_sequence(config.get(key))
        if values is None:
            continue
        for index, value in enumerate(values):
            reference = _attribute_reference_value(value)
            if reference is not None:
                references.append(
                    AttributeReference(
                        value=reference,
                        path=f"{path}.{key}[{index}]",
                    ),
                )
    return tuple(references)


def _attribute_reference_value(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    mapping_value = object_mapping(value)
    if mapping_value is None:
        return None
    for key in ("attribute_definition_id", "attribute_id", "attribute_external_id"):
        reference = mapping_value.get(key)
        if isinstance(reference, str) and reference.strip():
            return reference.strip()
    return None
