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
_AGENTIC_CONTEXT_RESOLVER_IMPLEMENTATION_ID = "document.extraction.agentic_context_resolver"
_CONTEXT_RESOLVER_MAX_ATTRIBUTE_COUNT = 500
_RUNTIME_CONFIG_KEYS = frozenset(
    {"document_type_id", "attributes", "metadata", "compatibility_external_ids"}
)


@dataclass(frozen=True, slots=True)
class OcrPipelineContextAttribute:
    """One document-type matrix attribute prepared for Context Resolver."""

    attribute_id: UUID
    attribute_external_id: str
    display_name: str
    value_type: str
    required: bool
    llm_context: str | None = None
    data_type: str | None = None
    value_source: str = "free_text"
    constraints: Mapping[str, object] | None = None
    allowed_values: tuple[str, ...] = ()
    dictionary_values: tuple[str, ...] = ()
    source: str = "ai"
    configured_required: bool | None = None
    missing_required_action: str | None = None
    metadata_value: str | None = None


@dataclass(frozen=True, slots=True)
class OcrPipelineContextMetadata:
    """One opted-in document metadata value prepared for Context Resolver."""

    key: str
    display_name: str
    value: str
    attribute_id: UUID | None = None


class OcrPipelineContextAttributeSource(Protocol):
    """Port for reading matrix attributes used by runtime Context Resolver steps."""

    async def list_context_attributes(
        self,
        *,
        document_type_id: UUID,
        metadata_values: Mapping[str, object],
    ) -> tuple[OcrPipelineContextAttribute, ...]: ...

    async def list_agentic_context_attributes(
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

    async def list_agentic_context_metadata(
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

    attributes_by_kind: dict[str, tuple[OcrPipelineContextAttribute, ...]] = {}
    metadata_by_kind: dict[str, tuple[OcrPipelineContextMetadata, ...]] = {}
    steps = cast(Sequence[object], steps_value)
    enriched_steps: list[object] = []
    for step in steps:
        resolver_kind = _context_resolver_kind(step)
        if resolver_kind is None:
            enriched_steps.append(step)
            continue
        attributes = attributes_by_kind.get(resolver_kind)
        if attributes is None:
            if resolver_kind == "agentic":
                attributes = await attribute_source.list_agentic_context_attributes(
                    document_type_id=document_type_id,
                    metadata_values=metadata_values,
                )
            else:
                attributes = await attribute_source.list_context_attributes(
                    document_type_id=document_type_id,
                    metadata_values=metadata_values,
                )
            attributes_by_kind[resolver_kind] = attributes
        metadata = metadata_by_kind.get(resolver_kind)
        if metadata is None:
            if resolver_kind == "agentic":
                metadata = await attribute_source.list_agentic_context_metadata(
                    document_type_id=document_type_id,
                    metadata_values=metadata_values,
                )
            else:
                metadata = await attribute_source.list_context_metadata(
                    document_type_id=document_type_id,
                    metadata_values=metadata_values,
                )
            metadata_by_kind[resolver_kind] = metadata
        enriched_steps.append(
            _step_with_context_attributes(
                cast(Mapping[str, object], step),
                document_type_id=document_type_id,
                attributes=attributes,
                metadata=metadata,
                agentic=resolver_kind == "agentic",
            ),
        )

    return {**dict(snapshot), "steps": enriched_steps}


def _context_resolver_kind(step: object) -> str | None:
    if not isinstance(step, Mapping):
        return None
    step_mapping = cast(Mapping[str, object], step)
    implementation_id = step_mapping.get("implementation_id")
    if implementation_id == _CONTEXT_RESOLVER_IMPLEMENTATION_ID:
        return "v1"
    if implementation_id == _AGENTIC_CONTEXT_RESOLVER_IMPLEMENTATION_ID:
        return "agentic"
    return None


def _step_with_context_attributes(
    step: Mapping[str, object],
    *,
    document_type_id: UUID,
    attributes: tuple[OcrPipelineContextAttribute, ...],
    metadata: tuple[OcrPipelineContextMetadata, ...],
    agentic: bool,
) -> JsonObject:
    if not attributes:
        raise ValueError("Context Resolver requires attributes assigned to the document type.")
    if len(attributes) > _CONTEXT_RESOLVER_MAX_ATTRIBUTE_COUNT:
        raise ValueError("Context Resolver attribute matrix exceeds the supported maximum.")

    config = _runtime_config(step.get("config"))
    config["document_type_id"] = str(document_type_id)
    if agentic:
        config["attributes"] = [_agentic_attribute_payload(attribute) for attribute in attributes]
        config["metadata"] = [_agentic_metadata_payload(item) for item in metadata]
        config["compatibility_external_ids"] = {
            str(attribute.attribute_id): attribute.attribute_external_id for attribute in attributes
        }
    else:
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


def _agentic_attribute_payload(
    attribute: OcrPipelineContextAttribute,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "attribute_id": str(attribute.attribute_id),
        "display_name": attribute.display_name,
        "data_type": attribute.data_type or attribute.value_type,
        "value_source": attribute.value_source,
        "constraints": dict(attribute.constraints or {}),
        "allowed_values": list(attribute.allowed_values),
        "dictionary_values": list(attribute.dictionary_values),
        "source": attribute.source,
        "configured_required": (
            attribute.required
            if attribute.configured_required is None
            else attribute.configured_required
        ),
        "effective_required": attribute.required,
        "missing_required_action": attribute.missing_required_action,
    }
    if (llm_context := _runtime_llm_context(attribute.llm_context)) is not None:
        payload["llm_context"] = llm_context
    if attribute.metadata_value is not None:
        payload["metadata_value"] = attribute.metadata_value
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


def _agentic_metadata_payload(metadata: OcrPipelineContextMetadata) -> dict[str, str]:
    if metadata.attribute_id is None:
        raise ValueError("Agentic Context Resolver metadata requires an attribute UUID.")
    return {
        "attribute_id": str(metadata.attribute_id),
        "display_name": metadata.display_name,
        "value": metadata.value,
    }


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
