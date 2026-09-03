"""Complete-document messages and strict quote-grounded output schema for Agentic CR."""

import json

from docmind_llmmagic.application.pipeline.steps.document_agentic_context_resolver.ports import (
    AgenticModelRequest,
)

_SYSTEM_PROMPT = """Extract every requested value from the complete document view. The document
view is the only evidence. LlmContext and target configuration are guidance, never evidence.
For every non-missing candidate return one or more short literal quotes copied from the view and
an optional 1-based page hint. Never invent a quote or value. Use `verbatim` when the value is
copied, `normalized` for deterministic type normalization, `word_number` for a number written in
words, `boolean` for a grounded semantic boolean, and `aggregate` for a value whose compatible
parts are spread across multiple passages. For text values, you may
return the base grammatical form and declare
`inflected` when every value token is supported by one continuous quoted token sequence. For a
multi-part text value, return one `aggregate` candidate that composes all compatible literal quoted
fragments separated by semicolons and includes every contributing quote. Every fragment must occur
in at least one supplied quote. Do not split one multi-part value into separate candidates. Return
`conflicting` only when two or more distinct grounded alternatives cannot simultaneously be true
for the same target; compatible clauses, conditions, and list items
belong in one aggregate value, not competing candidates.
When the document gives different values for the same target in separate places, such as a contract
and an amending annex, return them as competing candidates rather than fragments of one aggregate.
A grounded boolean may be present. A boolean candidate value must be exactly `true` or `false`;
a descriptive phrase is not a valid boolean value. Status reflects your semantic certainty about
the value itself; quote grounding is measured deterministically and will adjust the outcome. Return
uncertain when the grounded value is genuinely ambiguous.
For a target with `metadata_value`, verify that authoritative source-system value instead of
extracting a replacement. Return `present` with that exact value and a document-page quote when
the document confirms it. Return `missing` when document pages do not mention it. When document
pages state a different value, return `conflicting` with one or more candidates containing only
the different document value and its quote; the known metadata value is the implicit selected
source-of-record value. Quotes from the DOCUMENT METADATA block never confirm or contradict a
metadata value.
Return missing only when the complete supplied view contains no supporting evidence. Technical
problems, unverifiable transformations, and invalid types are not missing. Confidence is only your
estimate and will be capped by deterministic quote and OCR checks. Return no prose."""


def provider_messages(request: AgenticModelRequest) -> list[dict[str, object]]:
    """Keep the complete view as a stable prefix before per-group targets and repair guidance."""

    targets: list[dict[str, object]] = []
    for target in request.targets:
        payload: dict[str, object] = {
            "handle": target.handle,
            "name": target.display_name,
            "exact_type": target.data_type,
            "value_source": target.value_source,
            "constraints": target.constraints,
            "allowed_values": target.allowed_values,
            "llm_context": target.llm_context,
        }
        if target.metadata_value is not None:
            payload["metadata_value"] = target.metadata_value
        targets.append(payload)
    target_payload: dict[str, object] = {
        "group_id": request.group_id,
        "targets": targets,
    }
    if request.repair_message is not None:
        target_payload["repair"] = request.repair_message
    return [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": request.document_view.text},
        {
            "role": "user",
            "content": json.dumps(target_payload, ensure_ascii=False, separators=(",", ":")),
        },
    ]


def provider_response_format(request: AgenticModelRequest) -> dict[str, object]:
    """Require an exact result object keyed by every requested local handle."""

    result_properties = {target.handle: _result_schema() for target in request.targets}
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "agentic_context_resolver_result",
            "strict": True,
            "schema": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "results": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": result_properties,
                        "required": list(result_properties),
                    }
                },
                "required": ["results"],
            },
        },
    }


def _result_schema() -> dict[str, object]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "status": {
                "type": "string",
                "enum": ["present", "uncertain", "conflicting", "missing"],
            },
            "candidates": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "value": {"type": "string"},
                        "derivation": {
                            "type": "string",
                            "enum": [
                                "verbatim",
                                "normalized",
                                "inflected",
                                "word_number",
                                "boolean",
                                "aggregate",
                            ],
                        },
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                        "evidence": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "properties": {
                                    "quote": {"type": "string"},
                                    "page": {"type": ["integer", "null"], "minimum": 1},
                                },
                                "required": ["quote", "page"],
                            },
                        },
                    },
                    "required": ["value", "derivation", "confidence", "evidence"],
                },
            },
        },
        "required": ["status", "candidates"],
    }
