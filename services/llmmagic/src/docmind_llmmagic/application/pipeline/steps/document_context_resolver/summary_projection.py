"""Projection of legacy Context Resolver results into the Agentic summary schema."""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from docmind_llmmagic.application.pipeline.steps.document_context_resolver.config import (
    ContextResolverConfig,
)
from docmind_llmmagic.application.pipeline.steps.document_context_resolver.coverage import (
    coverage_attributes,
)
from docmind_llmmagic.application.pipeline.steps.document_context_resolver.ports import (
    ContextResolverModelAttribute,
    ContextResolverModelResult,
    EvidenceUnit,
)
from docmind_llmmagic.application.pipeline.steps.document_context_resolver.result_mapping import (
    resolved_attributes,
)
from docmind_llmmagic.application.pipeline.steps.document_context_resolver.retrieval import (
    ContextResolverBatch,
)
from docmind_llmmagic.application.pipeline.steps.document_context_resolver.workflow import (
    ContextResolverBatchOutcome,
    ContextResolverWorkflowResult,
)
from docmind_llmmagic.domain.pipeline.context_resolution import (
    ContextAttributeSpec,
    ResolvedAttributeStatus,
    ResolvedDocumentAttribute,
)

_FIELD_ORDER_SCOPE = (
    "Resolver evidence order only; API source mapping and Review ordered-source "
    "filtering are not reflected."
)


@dataclass(frozen=True, slots=True)
class LegacySummaryProjection:
    """Safe observation payload plus its outer observation status."""

    status: str
    summary: str
    output: dict[str, object]
    warning_count: int


def build_completed_summary(
    *,
    config: ContextResolverConfig,
    result: ContextResolverWorkflowResult,
    primary_result: tuple[ContextResolverModelAttribute, ...],
    batches: tuple[ContextResolverBatch, ...],
    outcomes: tuple[ContextResolverBatchOutcome, ...],
    duration_seconds: float,
) -> LegacySummaryProjection:
    """Build the stable schema-v2 payload using only safe result metadata."""

    attributes = resolved_attributes(
        config=config,
        model_result=result.model_result,
        evidence_catalog=result.evidence_catalog,
    )
    coverage_ids: set[str] = set()
    if result.metrics.coverage_fallback_attribute_count:
        coverage_ids = {
            attribute.attribute_external_id
            for attribute in coverage_attributes(
                config=config,
                primary_result=ContextResolverModelResult(attributes=primary_result),
            )
        }
    handles = handles_for_attributes(config.attributes)
    groups = _groups(batches, outcomes, handles=handles, coverage_ids=coverage_ids)
    handle_reports = _handle_reports(
        config.attributes,
        attributes,
        result=result,
        groups=groups,
        handles=handles,
        coverage_ids=coverage_ids,
    )
    repair_count = sum(max(0, outcome.attempts - 1) for outcome in outcomes)
    warning_codes = ["CONTEXT_RESOLVER_RETRY_APPLIED"] if repair_count else []
    status = "succeeded_with_warnings" if warning_codes else "succeeded"
    missing_count = sum(
        attribute.status == ResolvedAttributeStatus.MISSING for attribute in attributes
    )
    business_missing_count = sum(
        attribute.status == ResolvedAttributeStatus.MISSING
        and attribute.attribute_external_id in coverage_ids
        for attribute in attributes
    )
    review_required_count = sum(attribute.requires_review for attribute in attributes)
    summary = (
        f"Context Resolver completed {len(attributes)} AI attributes "
        f"in {len(batches)} groups; {missing_count} fields are empty, "
        f"{business_missing_count} were confirmed absent after the second pass, "
        "0 need the second pass, 0 used a deterministic fallback, and "
        f"{review_required_count} require review."
    )
    output: dict[str, object] = {
        "schema_version": 2,
        "status": status,
        "summary": summary,
        "attribute_counts": _attribute_counts(
            attributes,
            coverage_ids=coverage_ids,
            review_required_count=review_required_count,
        ),
        "execution": {
            "group_count": len(batches),
            "duration_seconds": duration_seconds,
            "model_turn_count": result.metrics.batch_count + repair_count,
            "provider_request_count": result.metrics.model_request_count,
            "tool_call_count": 0,
            "repair_count": repair_count,
            "coverage_retry_attribute_count": result.metrics.coverage_fallback_attribute_count,
            "searched_attribute_count": len(attributes),
            "input_token_count": 0,
            "output_token_count": 0,
            "quote_reference_count": 0,
            "truncated_provider_response_count": 0,
        },
        "warning_codes": warning_codes,
        "final_diagnostic_codes": sorted(
            {
                code
                for report in handle_reports
                for code in cast(list[object], report["diagnostic_codes"])
                if isinstance(code, str)
            }
        ),
        "groups": [report for _external_ids, report in groups],
        "handles": handle_reports,
        "field_order": _field_order(handle_reports),
    }
    return LegacySummaryProjection(status, summary, output, len(warning_codes))


def handles_for_attributes(attributes: tuple[ContextAttributeSpec, ...]) -> dict[str, str]:
    """Return Agentic-compatible opaque handles in configuration order."""

    return {
        attribute.attribute_external_id: f"A{index:02d}"
        for index, attribute in enumerate(attributes, start=1)
    }


def _attribute_counts(
    attributes: tuple[ResolvedDocumentAttribute, ...],
    *,
    coverage_ids: set[str],
    review_required_count: int,
) -> dict[str, int]:
    business_missing = tuple(
        attribute
        for attribute in attributes
        if attribute.status == ResolvedAttributeStatus.MISSING
        and attribute.attribute_external_id in coverage_ids
    )
    return {
        "total": len(attributes),
        "present": sum(
            attribute.status == ResolvedAttributeStatus.PRESENT for attribute in attributes
        ),
        "uncertain": sum(
            attribute.status == ResolvedAttributeStatus.UNCERTAIN for attribute in attributes
        ),
        "missing": sum(
            attribute.status == ResolvedAttributeStatus.MISSING for attribute in attributes
        ),
        "conflicting": sum(
            attribute.status == ResolvedAttributeStatus.CONFLICTING for attribute in attributes
        ),
        "business_missing": len(business_missing),
        "business_missing_required": sum(attribute.required for attribute in business_missing),
        "business_missing_optional": sum(not attribute.required for attribute in business_missing),
        "coverage_pending": 0,
        "validation_fallback_missing": 0,
        "timeout_fallback_missing": 0,
        "provider_failure_missing": 0,
        "fallback_missing": 0,
        "review_required": review_required_count,
    }


def _groups(
    batches: tuple[ContextResolverBatch, ...],
    outcomes: tuple[ContextResolverBatchOutcome, ...],
    *,
    handles: dict[str, str],
    coverage_ids: set[str],
) -> list[tuple[frozenset[str], dict[str, object]]]:
    outcomes_by_id = {outcome.batch_id: outcome for outcome in outcomes}
    reports: list[tuple[frozenset[str], dict[str, object]]] = []
    for index, batch in enumerate(batches, start=1):
        outcome = outcomes_by_id[batch.batch_id]
        external_ids = frozenset(item.attribute_external_id for item in batch.attributes)
        repair_count = max(0, outcome.attempts - 1)
        issue_codes = ["CONTEXT_RESOLVER_RETRY_APPLIED"] if repair_count else []
        reports.append(
            (
                external_ids,
                {
                    "group_id": f"G{index:03d}",
                    "status": "succeeded_with_warnings" if issue_codes else "succeeded",
                    "handles": [handles[item.attribute_external_id] for item in batch.attributes],
                    "model_turn_count": outcome.attempts,
                    "provider_request_count": outcome.provider_request_count,
                    "repair_count": repair_count,
                    "coverage_retry_attribute_count": len(external_ids & coverage_ids),
                    "truncated_provider_response_count": 0,
                    "truncated_response_count": 0,
                    "finish_reason": None,
                    "duration_seconds": 0.0,
                    "fallback_missing_count": 0,
                    "timeout_fallback_missing_count": 0,
                    "provider_failure_missing_count": 0,
                    "issue_codes": issue_codes,
                },
            )
        )
    return reports


def _handle_reports(
    specs: tuple[ContextAttributeSpec, ...],
    attributes: tuple[ResolvedDocumentAttribute, ...],
    *,
    result: ContextResolverWorkflowResult,
    groups: list[tuple[frozenset[str], dict[str, object]]],
    handles: dict[str, str],
    coverage_ids: set[str],
) -> list[dict[str, object]]:
    evidence_by_id = {unit.evidence_id: unit for unit in result.evidence_catalog}
    model_by_id = {item.attribute_external_id: item for item in result.model_result.attributes}
    resolved_by_id = {item.attribute_external_id: item for item in attributes}
    reports: list[dict[str, object]] = []
    for spec in specs:
        external_id = spec.attribute_external_id
        model_attribute = model_by_id[external_id]
        resolved = resolved_by_id[external_id]
        evidence = tuple(evidence_by_id[item] for item in model_attribute.evidence_ids)
        location = _document_location(evidence)
        diagnostic_codes = [code.value for code in resolved.reason_codes]
        if resolved.status == ResolvedAttributeStatus.MISSING and external_id in coverage_ids:
            diagnostic_codes.append("BUSINESS_MISSING")
        group_id = next(
            report["group_id"] for external_ids, report in groups if external_id in external_ids
        )
        reports.append(
            {
                "handle": handles[external_id],
                "display_name": spec.display_name,
                "data_type": spec.value_type or "legacy_scalar",
                "page_number": location[0] if location is not None else None,
                "order_index": location[1] if location is not None else None,
                "group_id": group_id,
                "status": resolved.status.value,
                "outcome": (
                    "business_missing"
                    if resolved.status == ResolvedAttributeStatus.MISSING
                    and external_id in coverage_ids
                    else resolved.status.value
                ),
                "required": spec.required,
                "requires_review": resolved.requires_review,
                "search_completed": True,
                "candidate_count": 0,
                "evidence_count": len(evidence),
                "derivation": None,
                "quote_match_score": None,
                "page_hint_missed": False,
                "ambiguous": False,
                "quote_count": 0,
                "confidence": resolved.confidence_score,
                "diagnostic_codes": list(dict.fromkeys(diagnostic_codes)),
            }
        )
    return reports


def _document_location(evidence: tuple[EvidenceUnit, ...]) -> tuple[int, int] | None:
    return min(
        (
            (unit.page_number, unit.order)
            for unit in evidence
            if unit.page_number is not None and unit.page_number > 0 and unit.order >= 0
        ),
        default=None,
    )


def _field_order(handles: list[dict[str, object]]) -> dict[str, object]:
    located: list[tuple[int, int, int, str]] = []
    without_location: list[str] = []
    for index, handle in enumerate(handles):
        page_number = handle["page_number"]
        order_index = handle["order_index"]
        display_name = str(handle["display_name"])
        if not isinstance(page_number, int) or not isinstance(order_index, int):
            without_location.append(display_name)
            continue
        located.append((page_number, order_index, index, display_name))
    located.sort(key=lambda item: item[:3])
    return {
        "scope": _FIELD_ORDER_SCOPE,
        "located": [display_name for _, _, _, display_name in located],
        "without_location": without_location,
    }
