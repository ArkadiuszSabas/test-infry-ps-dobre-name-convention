"""Runtime Context Resolver configuration for OCR pipeline runs."""

import json
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol, cast
from uuid import UUID

from docmind_api.domain.attributes.constants import ATTRIBUTE_LLM_CONTEXT_MAX_LENGTH
from docmind_api.domain.attributes.models import AttributeDataType
from docmind_api.domain.ocr_pipeline_runs.models import JsonObject

_CONTEXT_RESOLVER_IMPLEMENTATION_ID = "document.extraction.context_resolver"
_CONTEXT_RESOLVER_MAX_ATTRIBUTE_COUNT = 500
_RUNTIME_CONFIG_KEYS = frozenset({"document_type_id", "attributes", "metadata"})


@dataclass(frozen=True, slots=True)
class OcrPipelineContextAttribute:
    """One document-type matrix attribute prepared for Context Resolver."""

    attribute_id: UUID
    attribute_external_id: str
    display_name: str
    value_type: str
    required: bool
    llm_context: str | None = None


@dataclass(frozen=True, slots=True)
class OcrPipelineContextMetadata:
    """One opted-in document metadata value prepared for Context Resolver."""

    key: str
    display_name: str
    value: str


class OcrPipelineContextAttributeSource(Protocol):
    """Port for reading matrix attributes used by runtime Context Resolver steps."""

    async def list_context_attributes(
        self,
        *,
        document_type_id: UUID,
        metadata_values: Mapping[str, object],
    ) -> tuple[OcrPipelineContextAttribute, ...]: ...

    async def list_context_metadata(
        self,
        *,
        document_type_id: UUID,
        metadata_values: Mapping[str, object],
    ) -> tuple[OcrPipelineContextMetadata, ...]: ...


async def compiled_snapshot_with_context_attributes(
    snapshot: Mapping[str, object],
    *,
    document_type_id: UUID,
    metadata_values: Mapping[str, object],
    attribute_source: OcrPipelineContextAttributeSource,
) -> JsonObject:
    """Return a run snapshot whose Context Resolver steps use document matrix attributes."""

    steps_value = snapshot.get("steps")
    if not isinstance(steps_value, list | tuple):
        return dict(snapshot)

    attributes: tuple[OcrPipelineContextAttribute, ...] | None = None
    metadata: tuple[OcrPipelineContextMetadata, ...] | None = None
    steps = cast(Sequence[object], steps_value)
    enriched_steps: list[object] = []
    for step in steps:
        if not _is_context_resolver_step(step):
            enriched_steps.append(step)
            continue
        if attributes is None:
            attributes = await attribute_source.list_context_attributes(
                document_type_id=document_type_id,
                metadata_values=metadata_values,
            )
        if metadata is None:
            metadata = await attribute_source.list_context_metadata(
                document_type_id=document_type_id,
                metadata_values=metadata_values,
            )
        enriched_steps.append(
            _step_with_context_attributes(
                cast(Mapping[str, object], step),
                document_type_id=document_type_id,
                attributes=attributes,
                metadata=metadata,
            ),
        )

    return {**dict(snapshot), "steps": enriched_steps}


def _is_context_resolver_step(step: object) -> bool:
    if not isinstance(step, Mapping):
        return False
    step_mapping = cast(Mapping[str, object], step)
    return step_mapping.get("implementation_id") == _CONTEXT_RESOLVER_IMPLEMENTATION_ID


def _step_with_context_attributes(
    step: Mapping[str, object],
    *,
    document_type_id: UUID,
    attributes: tuple[OcrPipelineContextAttribute, ...],
    metadata: tuple[OcrPipelineContextMetadata, ...],
) -> JsonObject:
    if not attributes:
        raise ValueError("Context Resolver requires attributes assigned to the document type.")
    if len(attributes) > _CONTEXT_RESOLVER_MAX_ATTRIBUTE_COUNT:
        raise ValueError("Context Resolver attribute matrix exceeds the supported maximum.")

    config = _runtime_config(step.get("config"))
    config["document_type_id"] = str(document_type_id)
    config["attributes"] = [_attribute_payload(attribute) for attribute in attributes]
    config["metadata"] = [_metadata_payload(item) for item in metadata]
    return {**dict(step), "config": config}


def _runtime_config(value: object) -> dict[str, object]:
    if not isinstance(value, Mapping):
        return {}
    return {
        str(key): item
        for key, item in cast(Mapping[object, object], value).items()
        if isinstance(key, str) and key not in _RUNTIME_CONFIG_KEYS
    }


def _attribute_payload(attribute: OcrPipelineContextAttribute) -> dict[str, object]:
    payload: dict[str, object] = {
        "attribute_id": str(attribute.attribute_id),
        "attribute_external_id": attribute.attribute_external_id,
        "display_name": attribute.display_name,
        "value_type": attribute.value_type,
        "required": attribute.required,
    }
    if (llm_context := _runtime_llm_context(attribute.llm_context)) is not None:
        payload["llm_context"] = llm_context
    return payload


def _runtime_llm_context(value: str | None) -> str | None:
    if value is None or not value.strip():
        return None
    sanitized = "".join(
        character
        if character in {"\n", "\r", "\t"} or unicodedata.category(character) != "Cc"
        else " "
        for character in value
    )
    return sanitized[:ATTRIBUTE_LLM_CONTEXT_MAX_LENGTH]


def _metadata_payload(metadata: OcrPipelineContextMetadata) -> dict[str, str]:
    return {"key": metadata.key, "display_name": metadata.display_name, "value": metadata.value}


def context_metadata_value(value: object) -> str | None:
    """Render one JSON-compatible metadata scalar for a bounded LLM prompt."""

    if value is None:
        return None
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, bool | int | float):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return None


def context_value_type(data_type: AttributeDataType) -> str:
    """Map API attribute data types to Context Resolver value-type hints."""

    if data_type == AttributeDataType.LEGACY_SCALAR:
        return AttributeDataType.STRING.value
    if data_type == AttributeDataType.DATETIME:
        return AttributeDataType.DATE.value
    return data_type.value
