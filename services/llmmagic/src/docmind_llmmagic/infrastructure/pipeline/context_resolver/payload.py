"""Compact provider payload for one Context Resolver batch."""

import json

from docmind_llmmagic.application.pipeline.steps.document_context_resolver.ports import (
    ContextResolverModelRequest,
    EvidenceUnit,
)
from docmind_llmmagic.domain.pipeline.context_resolution import (
    ContextAttributeSpec,
    ResolvedAttributeSourceKind,
)


def request_data(request: ContextResolverModelRequest) -> dict[str, object]:
    """Build the single JSON-compatible provider data projection."""

    return {
        "attributes": {
            attribute.attribute_external_id: _attribute_payload(attribute)
            for attribute in request.attributes
        },
        "evidence": [_evidence_payload(unit) for unit in request.evidence],
    }


def serialize_provider_data(data: dict[str, object]) -> str:
    """Serialize provider data compactly without changing its structure."""

    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def _attribute_payload(attribute: ContextAttributeSpec) -> dict[str, object]:
    return {
        "display_name": attribute.display_name,
        "aliases": list(attribute.aliases),
        "value_type": attribute.value_type,
        "extraction_hint": attribute.extraction_hint,
        "llm_context": attribute.llm_context,
    }


def _evidence_payload(unit: EvidenceUnit) -> dict[str, object]:
    kinds = {
        ResolvedAttributeSourceKind.OCR_KEY_VALUE: "key_value",
        ResolvedAttributeSourceKind.OCR_LINE: "line",
        ResolvedAttributeSourceKind.OCR_DOCUMENT: "text",
        ResolvedAttributeSourceKind.DOCUMENT_METADATA: "metadata",
    }
    payload: dict[str, object] = {
        "id": unit.evidence_id,
        "kind": kinds[unit.kind],
        "confidence": unit.confidence,
    }
    if unit.kind in {
        ResolvedAttributeSourceKind.OCR_KEY_VALUE,
        ResolvedAttributeSourceKind.DOCUMENT_METADATA,
    }:
        payload["label"] = unit.label
        payload["value"] = unit.value
    else:
        payload["text"] = unit.text
    return payload
