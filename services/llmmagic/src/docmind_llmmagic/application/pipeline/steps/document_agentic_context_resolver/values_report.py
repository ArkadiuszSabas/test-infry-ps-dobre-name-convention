"""FULL-capture observation with deterministic Agentic CR values and evidence."""

from docmind_llmmagic.application.pipeline.observability import (
    ObservationType,
    PipelineObserver,
    TraceCaptureMode,
)

from .document_view import DocumentSource
from .validation import ValidatedDecision


def observe_values_report(
    *,
    observer: PipelineObserver,
    capture_mode: TraceCaptureMode,
    grouped_decisions: tuple[tuple[ValidatedDecision, ...], ...],
    status: str,
    pipeline_id: str,
    run_id: str,
    step_id: str,
    user_id: str | None,
    document_id: str | None,
) -> None:
    """Emit values only for the explicitly PII-bearing FULL capture mode."""

    if capture_mode is not TraceCaptureMode.FULL:
        return
    output = build_values_report(status=status, grouped_decisions=grouped_decisions)
    value_count = sum(len(decisions) for decisions in grouped_decisions)
    metadata: dict[str, object] = {
        "resolver": "agentic",
        "pipeline_id": pipeline_id,
        "run_id": run_id,
        "step_id": step_id,
        "status": status,
        "capture_mode": capture_mode.value,
    }
    if document_id is not None:
        metadata["document_id"] = document_id
    with observer.observe(
        observation_type=ObservationType.SPAN,
        name="agentic-context-resolver.values",
        user_id=user_id,
        session_id=run_id,
        metadata=metadata,
    ) as observation:
        update: dict[str, object] = {
            "status_message": f"Agentic Context Resolver captured {value_count} final values.",
            "output": output,
            "metadata": {
                "resolver": "agentic",
                "status": status,
                "value_count": value_count,
                **({"document_id": document_id} if document_id is not None else {}),
            },
        }
        if status != "succeeded":
            update["level"] = "WARNING"
        observation.update(**update)


def build_values_report(
    *,
    status: str,
    grouped_decisions: tuple[tuple[ValidatedDecision, ...], ...],
) -> dict[str, object]:
    """Serialize final decisions without another provider call."""

    return {
        "schema_version": 1,
        "status": status,
        "values": [
            _decision_report(group_index, decision)
            for group_index, decisions in enumerate(grouped_decisions, start=1)
            for decision in decisions
        ],
    }


def _decision_report(group_index: int, decision: ValidatedDecision) -> dict[str, object]:
    attribute = decision.attribute
    return {
        "handle": attribute.handle,
        "group_id": f"G{group_index:03d}",
        "display_name": attribute.display_name,
        "data_type": attribute.data_type,
        "effective_required": attribute.effective_required,
        "constraints": {key: attribute.constraints[key] for key in sorted(attribute.constraints)},
        "status": decision.status,
        "value": decision.value,
        "confidence": decision.confidence,
        "evidence": [_source_report(source) for source in decision.evidence],
        "evidence_quotes": list(decision.evidence_quotes),
        "derivation": decision.derivation,
        "quote_match_score": decision.quote_match_score,
        "page_hint_missed": decision.page_hint_missed,
        "ambiguous": decision.ambiguous,
        "quote_reference_count": decision.quote_reference_count,
        "candidate_count": decision.candidate_count,
        "diagnostic_codes": list(decision.diagnostic_codes),
        "model_output_invalid": decision.model_output_invalid,
        "requires_review": decision.requires_review,
    }


def _source_report(source: DocumentSource) -> dict[str, object]:
    return {
        "kind": source.kind,
        "order": source.order,
        "page_number": source.page_number,
        "line_number": source.line_number,
        "key_value_index": source.key_value_index,
        "confidence": source.confidence,
        "bounding_polygon": list(source.bounding_polygon),
    }
