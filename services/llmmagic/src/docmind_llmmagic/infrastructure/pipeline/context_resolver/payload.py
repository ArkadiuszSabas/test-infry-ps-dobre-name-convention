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


def request_payload(request: ContextResolverModelRequest) -> str:
    """Serialize compact attribute definitions first and untrusted evidence last."""

    payload = {
        "attributes": {
            attribute.attribute_external_id: _attribute_payload(attribute)
            for attribute in request.attributes
        },
        "evidence": [_evidence_payload(unit) for unit in request.evidence],
    }
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


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
