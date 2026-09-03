"""Dynamic strict JSON schema for one Context Resolver batch."""

from collections.abc import Mapping, Sequence

from docmind_llmmagic.application.pipeline.steps.document_context_resolver import (
    model_contract_limits,
)


def context_resolver_response_format(
    *,
    expected_attribute_ids: Sequence[str],
    evidence_ids: Sequence[str],
) -> Mapping[str, object]:
    """Require every expected attribute key and forbid all unknown keys."""

    result_properties = {
        attribute_id: _attribute_result_schema(evidence_ids)
        for attribute_id in expected_attribute_ids
    }
    schema: dict[str, object] = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "results": {
                "type": "object",
                "additionalProperties": False,
                "properties": result_properties,
                "required": list(expected_attribute_ids),
            }
        },
        "required": ["results"],
    }
    definitions: dict[str, object] = {
        "resolution": {
            "type": "string",
            "enum": list(model_contract_limits.CONTEXT_RESOLVER_RESOLUTION_VALUES),
        }
    }
    if evidence_ids:
        definitions["evidence_id"] = {
            "type": "string",
            "enum": list(evidence_ids),
        }
    schema["$defs"] = definitions
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "context_resolver_batch_response",
            "strict": True,
            "schema": schema,
        },
    }


def _attribute_result_schema(evidence_ids: Sequence[str]) -> dict[str, object]:
    evidence_item: dict[str, object] = (
        {"$ref": "#/$defs/evidence_id"} if evidence_ids else {"type": "string"}
    )
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "value": {"type": ["string", "null"]},
            "confidence": {"type": ["number", "null"]},
            "evidence_ids": {
                "type": "array",
                "items": evidence_item,
            },
            "resolution": {"$ref": "#/$defs/resolution"},
        },
        "required": ["value", "confidence", "evidence_ids", "resolution"],
    }
