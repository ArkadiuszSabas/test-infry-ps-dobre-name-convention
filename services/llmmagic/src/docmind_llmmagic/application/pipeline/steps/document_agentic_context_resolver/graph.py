"""Bounded concurrent complete-document extraction and deterministic validation."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, replace
from time import perf_counter

from docmind_llmmagic.application.pipeline.observability import (
    BestEffortPipelineObserver,
    NoopPipelineObserver,
    ObservationType,
    PipelineObserver,
    TraceCaptureMode,
)
from docmind_llmmagic.application.pipeline.steps.document_context_resolver.errors import (
    provider_request_count_from_error,
)
from docmind_llmmagic.domain.pipeline.errors import PipelineStepError

from .config import AgenticAttributeSpec, AgenticContextResolverConfig
from .constants import (
    AGENTIC_MAX_COMPLETION_TOKENS,
    AGENTIC_MAX_CONCURRENCY,
    AGENTIC_MAX_GROUP_ESTIMATED_OUTPUT_TOKENS,
)
from .document_view import DocumentView
from .grouping import grouped_attributes
from .ports import AgenticContextResolverModelClient, AgenticModelRequest, AgenticModelTurn
from .validation import (
    AgenticValidationError,
    AgenticValidationIssue,
    ValidatedDecision,
    validate_group_output,
)
from .values_report import observe_values_report
from .workflow_support import (
    merge_decisions,
    merge_second_pass_decisions,
    model_target,
    repair_message,
    requires_second_pass,
)
from .workflow_validation import empty_validation_fallback

_EXCESSIVE_CONFLICT_CANDIDATE_COUNT = 3
_TEXT_CONFLICT_DATA_TYPES = frozenset({"string", "legacy_scalar"})
_PROVIDER_REQUEST_FAILED = "PROVIDER_REQUEST_FAILED"
_PROVIDER_MODEL_ERROR = "CONTEXT_RESOLVER_MODEL_REQUEST_FAILED"


@dataclass(frozen=True, slots=True)
class _PassState:
    decisions: tuple[ValidatedDecision, ...]
    turns: tuple[AgenticModelTurn, ...]
    repair_count: int
    issue_codes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _GroupState:
    group_id: str
    decisions: tuple[ValidatedDecision, ...]
    model_turn_count: int
    provider_request_count: int
    repair_count: int
    input_token_count: int
    output_token_count: int
    truncated_provider_response_count: int
    finish_reason: str | None
    issue_codes: tuple[str, ...]
    duration_seconds: float = 0.0
    coverage_retry_attribute_count: int = 0
    timeout_fallback_count: int = 0
    provider_failure_fallback_count: int = 0


@dataclass(frozen=True, slots=True)
class AgenticWorkflowResult:
    """Complete all-groups result with compatibility metrics during migration."""

    decisions: tuple[ValidatedDecision, ...]
    group_count: int
    model_turn_count: int
    provider_request_count: int
    tool_round_count: int
    tool_call_count: int
    repair_count: int
    searched_attribute_count: int
    input_token_count: int
    output_token_count: int
    unique_evidence_count: int
    evidence_reference_count: int
    repeated_evidence_reference_count: int
    evidence_char_count: int
    search_candidate_reference_count: int
    zero_candidate_attribute_count: int
    truncated_search_attribute_count: int
    model_search_term_count: int
    validation_fallback_missing_attribute_count: int
    timeout_fallback_missing_attribute_count: int
    provider_failure_missing_attribute_count: int
    quote_reference_count: int
    coverage_pending_attribute_count: int
    coverage_retry_attribute_count: int
    truncated_provider_response_count: int


class AgenticContextResolverGraph:
    """Execute bounded complete-document groups with deterministic coverage passes."""

    def __init__(
        self,
        *,
        observer: PipelineObserver | None = None,
        trace_capture_mode: TraceCaptureMode = TraceCaptureMode.METADATA,
    ) -> None:
        self._observer = (
            BestEffortPipelineObserver(observer) if observer is not None else NoopPipelineObserver()
        )
        self._trace_capture_mode = trace_capture_mode

    @property
    def node_names(self) -> tuple[str, ...]:
        return ("agent", "validate")

    async def run(
        self,
        *,
        config: AgenticContextResolverConfig,
        document_view: DocumentView,
        model_client: AgenticContextResolverModelClient,
        pipeline_id: str,
        run_id: str,
        step_id: str,
        user_id: str | None,
        document_id: str | None = None,
    ) -> AgenticWorkflowResult:
        step_started_at = perf_counter()
        groups = grouped_attributes(
            config.ai_attributes,
            max_attributes=config.group_max_attributes,
            max_request_bytes=config.group_max_request_bytes,
            max_estimated_output_tokens=AGENTIC_MAX_GROUP_ESTIMATED_OUTPUT_TOKENS,
        )
        if not groups:
            workflow = _empty_workflow()
            self._observe_completed_summary(
                workflow=workflow,
                groups=(),
                states=(),
                duration_seconds=perf_counter() - step_started_at,
                pipeline_id=pipeline_id,
                run_id=run_id,
                step_id=step_id,
                user_id=user_id,
                document_id=document_id,
            )
            return workflow
        semaphore = asyncio.Semaphore(AGENTIC_MAX_CONCURRENCY)
        group_durations: dict[int, float] = {}
        provider_errors_by_index: dict[int, PipelineStepError] = {}

        async def execute(
            index: int,
            attributes: tuple[AgenticAttributeSpec, ...],
        ) -> _GroupState:
            async with semaphore:
                group_started_at = perf_counter()
                try:
                    try:
                        state = await self._run_group(
                            group_id=f"G{index:03d}",
                            attributes=attributes,
                            document_view=document_view,
                            model_client=model_client,
                            config=config,
                            pipeline_id=pipeline_id,
                            run_id=run_id,
                            step_id=step_id,
                            user_id=user_id,
                        )
                    except PipelineStepError as exc:
                        if exc.code != _PROVIDER_MODEL_ERROR:
                            raise
                        provider_errors_by_index[index] = exc
                        state = _provider_failure_fallback_state(
                            group_id=f"G{index:03d}",
                            attributes=attributes,
                            provider_request_count=provider_request_count_from_error(
                                exc,
                                default=1,
                            ),
                        )
                finally:
                    group_durations[index] = perf_counter() - group_started_at
                return replace(state, duration_seconds=group_durations[index])

        tasks = {
            asyncio.create_task(execute(index, attributes)): (index, attributes)
            for index, attributes in enumerate(groups, start=1)
        }
        states_by_index: dict[int, _GroupState] = {}
        try:
            done, pending = await asyncio.wait(
                tasks,
                timeout=config.step_timeout_seconds,
                return_when=asyncio.FIRST_EXCEPTION,
            )
            failed = tuple(
                sorted(
                    (task for task in done if task.exception() is not None),
                    key=lambda task: tasks[task][0],
                )
            )
            for task in done - set(failed):
                index, _ = tasks[task]
                states_by_index[index] = task.result()
            if failed:
                failed[0].result()
            if len(provider_errors_by_index) == len(groups):
                raise provider_errors_by_index[min(provider_errors_by_index)]
        except Exception as exc:
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            self._observe_failed_summary(
                config=config,
                groups=groups,
                states_by_index=states_by_index,
                pipeline_id=pipeline_id,
                run_id=run_id,
                step_id=step_id,
                user_id=user_id,
                document_id=document_id,
                error=exc,
            )
            raise

        if pending:
            for task in pending:
                task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)
            for task in pending:
                index, attributes = tasks[task]
                states_by_index[index] = _timeout_fallback_state(
                    group_id=f"G{index:03d}",
                    attributes=attributes,
                    duration_seconds=group_durations.get(index, 0.0),
                )

        states = tuple(states_by_index[index] for index in range(1, len(groups) + 1))
        decisions = tuple(decision for state in states for decision in state.decisions)
        evidence = tuple(source for decision in decisions for source in decision.evidence)
        unique_evidence = set(evidence)
        workflow = AgenticWorkflowResult(
            decisions=decisions,
            group_count=len(groups),
            model_turn_count=sum(state.model_turn_count for state in states),
            provider_request_count=sum(state.provider_request_count for state in states),
            tool_round_count=0,
            tool_call_count=0,
            repair_count=sum(state.repair_count for state in states),
            searched_attribute_count=sum(
                len(group)
                for index, group in enumerate(groups, start=1)
                if states_by_index[index].timeout_fallback_count == 0
                and states_by_index[index].provider_failure_fallback_count == 0
            ),
            input_token_count=sum(state.input_token_count for state in states),
            output_token_count=sum(state.output_token_count for state in states),
            unique_evidence_count=len(unique_evidence),
            evidence_reference_count=len(evidence),
            repeated_evidence_reference_count=len(evidence) - len(unique_evidence),
            evidence_char_count=0,
            search_candidate_reference_count=0,
            zero_candidate_attribute_count=0,
            truncated_search_attribute_count=0,
            model_search_term_count=0,
            validation_fallback_missing_attribute_count=sum(
                decision.model_output_invalid
                and "TIME_BUDGET_EXHAUSTED" not in decision.diagnostic_codes
                and _PROVIDER_REQUEST_FAILED not in decision.diagnostic_codes
                for decision in decisions
            ),
            timeout_fallback_missing_attribute_count=sum(
                state.timeout_fallback_count for state in states
            ),
            provider_failure_missing_attribute_count=sum(
                state.provider_failure_fallback_count for state in states
            ),
            quote_reference_count=sum(decision.quote_reference_count for decision in decisions),
            coverage_pending_attribute_count=sum(
                "SECOND_PASS_REQUIRED" in decision.diagnostic_codes for decision in decisions
            ),
            coverage_retry_attribute_count=sum(
                state.coverage_retry_attribute_count for state in states
            ),
            truncated_provider_response_count=sum(
                state.truncated_provider_response_count for state in states
            ),
        )
        self._observe_completed_summary(
            workflow=workflow,
            groups=groups,
            states=states,
            duration_seconds=perf_counter() - step_started_at,
            pipeline_id=pipeline_id,
            run_id=run_id,
            step_id=step_id,
            user_id=user_id,
            document_id=document_id,
        )
        return workflow

    async def _run_group(
        self,
        *,
        group_id: str,
        attributes: tuple[AgenticAttributeSpec, ...],
        document_view: DocumentView,
        model_client: AgenticContextResolverModelClient,
        config: AgenticContextResolverConfig,
        pipeline_id: str,
        run_id: str,
        step_id: str,
        user_id: str | None,
    ) -> _GroupState:
        primary = await self._run_pass(
            group_id=group_id,
            turn_start=1,
            attributes=attributes,
            document_view=document_view,
            model_client=model_client,
            config=config,
            pipeline_id=pipeline_id,
            run_id=run_id,
            step_id=step_id,
            user_id=user_id,
        )
        second_pass_attributes = tuple(
            decision.attribute
            for decision in primary.decisions
            if requires_second_pass(
                decision,
                present_confidence_threshold=(config.second_pass_present_confidence_threshold),
            )
        )
        if not second_pass_attributes:
            return _group_state(
                group_id,
                primary.decisions,
                primary.turns,
                repair_count=primary.repair_count,
                issue_codes=primary.issue_codes,
            )

        secondary = await self._run_pass(
            group_id=group_id,
            turn_start=len(primary.turns) + 1,
            attributes=second_pass_attributes,
            document_view=document_view,
            model_client=model_client,
            config=config,
            pipeline_id=pipeline_id,
            run_id=run_id,
            step_id=step_id,
            user_id=user_id,
        )
        decisions = merge_second_pass_decisions(
            attributes,
            primary.decisions,
            secondary.decisions,
            present_confidence_threshold=(config.second_pass_present_confidence_threshold),
        )
        return _group_state(
            group_id,
            decisions,
            (*primary.turns, *secondary.turns),
            repair_count=primary.repair_count + secondary.repair_count,
            issue_codes=tuple(sorted({*primary.issue_codes, *secondary.issue_codes})),
            coverage_retry_attribute_count=len(second_pass_attributes),
        )

    async def _run_pass(
        self,
        *,
        group_id: str,
        turn_start: int,
        attributes: tuple[AgenticAttributeSpec, ...],
        document_view: DocumentView,
        model_client: AgenticContextResolverModelClient,
        config: AgenticContextResolverConfig,
        pipeline_id: str,
        run_id: str,
        step_id: str,
        user_id: str | None,
    ) -> _PassState:
        turns: list[AgenticModelTurn] = []
        initial = await model_client.agentic_turn(
            _request(
                group_id=group_id,
                turn=turn_start,
                attributes=attributes,
                document_view=document_view,
                repair=None,
                config=config,
                pipeline_id=pipeline_id,
                run_id=run_id,
                step_id=step_id,
                user_id=user_id,
            )
        )
        turns.append(initial)
        partial: tuple[ValidatedDecision, ...] = ()
        issues: tuple[AgenticValidationIssue, ...]
        if initial.output_error_code is not None:
            issues = (AgenticValidationIssue(None, initial.output_error_code),)
        else:
            try:
                decisions = validate_group_output(
                    attributes=attributes,
                    results=initial.results,
                    document_view=document_view,
                )
                return _PassState(decisions, tuple(turns), 0, ())
            except AgenticValidationError as exc:
                partial = exc.valid_decisions
                issues = exc.issues

        repair_attributes = _attributes_for_issues(attributes, issues)
        error = AgenticValidationError(issues, valid_decisions=partial)
        repaired = await model_client.agentic_turn(
            _request(
                group_id=group_id,
                turn=turn_start + 1,
                attributes=repair_attributes,
                document_view=document_view,
                repair=repair_message(error),
                config=config,
                pipeline_id=pipeline_id,
                run_id=run_id,
                step_id=step_id,
                user_id=user_id,
            )
        )
        turns.append(repaired)
        issue_codes = {issue.code for issue in issues}
        if repaired.output_error_code is not None:
            fallback = empty_validation_fallback(
                attributes=repair_attributes,
                issues=issues,
                output_error_code=repaired.output_error_code,
            )
            issue_codes.add(repaired.output_error_code)
            return _PassState(
                merge_decisions(attributes, partial, fallback),
                tuple(turns),
                1,
                tuple(sorted(issue_codes)),
            )
        try:
            repaired_decisions = validate_group_output(
                attributes=repair_attributes,
                results=repaired.results,
                document_view=document_view,
            )
            decisions = merge_decisions(attributes, partial, repaired_decisions)
        except AgenticValidationError as exc:
            issue_codes.update(issue.code for issue in exc.issues)
            fallback = empty_validation_fallback(
                attributes=repair_attributes,
                issues=exc.issues,
            )
            decisions = merge_decisions(attributes, partial, exc.valid_decisions, fallback)
        return _PassState(
            decisions,
            tuple(turns),
            1,
            tuple(sorted(issue_codes)),
        )

    def _observe_completed_summary(
        self,
        *,
        workflow: AgenticWorkflowResult,
        groups: tuple[tuple[AgenticAttributeSpec, ...], ...],
        states: tuple[_GroupState, ...],
        duration_seconds: float,
        pipeline_id: str,
        run_id: str,
        step_id: str,
        user_id: str | None,
        document_id: str | None,
    ) -> None:
        fallback_count = (
            workflow.validation_fallback_missing_attribute_count
            + workflow.timeout_fallback_missing_attribute_count
            + workflow.provider_failure_missing_attribute_count
        )
        warning_codes = tuple(
            sorted(
                {code for state in states for code in state.issue_codes}
                | {
                    code
                    for decision in workflow.decisions
                    for code in decision.attribute.constraint_warning_codes
                }
            )
        )
        missing_count = sum(decision.status == "missing" for decision in workflow.decisions)
        review_required_count = sum(
            decision.requires_review or decision.model_output_invalid
            for decision in workflow.decisions
        )
        business_missing_count = sum(
            "BUSINESS_MISSING" in decision.diagnostic_codes for decision in workflow.decisions
        )
        status = (
            "degraded"
            if fallback_count
            else "succeeded_with_warnings"
            if warning_codes or workflow.coverage_pending_attribute_count
            else "succeeded"
        )
        group_reports = [
            _group_report(index, group, states[index - 1])
            for index, group in enumerate(groups, start=1)
        ]
        handle_reports = [
            _handle_report(index, decision)
            for index, state in enumerate(states, start=1)
            for decision in state.decisions
        ]
        field_order = _field_order_report(workflow.decisions)
        final_diagnostic_codes = sorted(
            {code for decision in workflow.decisions for code in _report_diagnostic_codes(decision)}
        )
        attribute_counts = {
            "total": len(workflow.decisions),
            "present": sum(decision.status == "present" for decision in workflow.decisions),
            "uncertain": sum(decision.status == "uncertain" for decision in workflow.decisions),
            "missing": missing_count,
            "conflicting": sum(decision.status == "conflicting" for decision in workflow.decisions),
            "business_missing": business_missing_count,
            "business_missing_required": sum(
                "BUSINESS_MISSING" in decision.diagnostic_codes
                and decision.attribute.effective_required
                for decision in workflow.decisions
            ),
            "business_missing_optional": sum(
                "BUSINESS_MISSING" in decision.diagnostic_codes
                and not decision.attribute.effective_required
                for decision in workflow.decisions
            ),
            "coverage_pending": workflow.coverage_pending_attribute_count,
            "validation_fallback_missing": (workflow.validation_fallback_missing_attribute_count),
            "timeout_fallback_missing": workflow.timeout_fallback_missing_attribute_count,
            "provider_failure_missing": workflow.provider_failure_missing_attribute_count,
            "fallback_missing": fallback_count,
            "review_required": review_required_count,
        }
        summary = (
            f"Agentic Context Resolver completed {len(workflow.decisions)} AI attributes "
            f"in {workflow.group_count} groups; {missing_count} fields are empty, "
            f"{business_missing_count} were confirmed absent after the second pass, "
            f"{workflow.coverage_pending_attribute_count} need the second pass, "
            f"{fallback_count} used a deterministic fallback, and "
            f"{review_required_count} require review."
        )
        with self._observer.observe(
            observation_type=ObservationType.SPAN,
            name="agentic-context-resolver.summary",
            user_id=user_id,
            session_id=run_id,
            metadata=_summary_observation_metadata(
                pipeline_id=pipeline_id,
                run_id=run_id,
                step_id=step_id,
                status=status,
                capture_mode=self._trace_capture_mode.value,
                document_id=document_id,
            ),
        ) as observation:
            update: dict[str, object] = {
                "status_message": summary,
                "output": {
                    "schema_version": 2,
                    "status": status,
                    "summary": summary,
                    "attribute_counts": attribute_counts,
                    "execution": {
                        "group_count": workflow.group_count,
                        "duration_seconds": duration_seconds,
                        "model_turn_count": workflow.model_turn_count,
                        "provider_request_count": workflow.provider_request_count,
                        "tool_call_count": workflow.tool_call_count,
                        "repair_count": workflow.repair_count,
                        "coverage_retry_attribute_count": (workflow.coverage_retry_attribute_count),
                        "searched_attribute_count": workflow.searched_attribute_count,
                        "input_token_count": workflow.input_token_count,
                        "output_token_count": workflow.output_token_count,
                        "quote_reference_count": workflow.quote_reference_count,
                        "truncated_provider_response_count": (
                            workflow.truncated_provider_response_count
                        ),
                    },
                    "warning_codes": list(warning_codes),
                    "final_diagnostic_codes": final_diagnostic_codes,
                    "groups": group_reports,
                    "handles": handle_reports,
                    "field_order": field_order,
                },
                "metadata": {
                    "resolver": "agentic",
                    "status": status,
                    **({"document_id": document_id} if document_id is not None else {}),
                    "warning_count": len(warning_codes),
                    "fallback_missing_count": fallback_count,
                    "timeout_fallback_missing_count": (
                        workflow.timeout_fallback_missing_attribute_count
                    ),
                    "provider_failure_missing_count": (
                        workflow.provider_failure_missing_attribute_count
                    ),
                    "coverage_pending_count": workflow.coverage_pending_attribute_count,
                    "coverage_retry_attribute_count": (workflow.coverage_retry_attribute_count),
                },
            }
            if status != "succeeded":
                update["level"] = "WARNING"
            observation.update(**update)
        observe_values_report(
            observer=self._observer,
            capture_mode=self._trace_capture_mode,
            grouped_decisions=tuple(state.decisions for state in states),
            status=status,
            pipeline_id=pipeline_id,
            run_id=run_id,
            step_id=step_id,
            user_id=user_id,
            document_id=document_id,
        )

    def _observe_failed_summary(
        self,
        *,
        config: AgenticContextResolverConfig,
        groups: tuple[tuple[AgenticAttributeSpec, ...], ...],
        states_by_index: dict[int, _GroupState],
        pipeline_id: str,
        run_id: str,
        step_id: str,
        user_id: str | None,
        document_id: str | None,
        error: Exception,
    ) -> None:
        raw_code = getattr(error, "code", None)
        failure_code = raw_code if isinstance(raw_code, str) else type(error).__name__
        group_reports = [
            _group_report(index, attributes, state)
            if (state := states_by_index.get(index)) is not None
            else {
                "group_id": f"G{index:03d}",
                "status": "not_completed",
                "handles": [attribute.handle for attribute in attributes],
                "coverage_retry_attribute_count": 0,
                "truncated_response_count": 0,
                "finish_reason": None,
                "duration_seconds": 0.0,
                "issue_codes": [],
            }
            for index, attributes in enumerate(groups, start=1)
        ]
        warning_codes = sorted(
            {code for state in states_by_index.values() for code in state.issue_codes}
            | {
                code
                for attribute in config.ai_attributes
                for code in attribute.constraint_warning_codes
            }
        )
        summary = (
            "Agentic Context Resolver failed before it could publish a complete review artifact."
        )
        with self._observer.observe(
            observation_type=ObservationType.SPAN,
            name="agentic-context-resolver.summary",
            user_id=user_id,
            session_id=run_id,
            metadata=_summary_observation_metadata(
                pipeline_id=pipeline_id,
                run_id=run_id,
                step_id=step_id,
                status="failed",
                capture_mode=self._trace_capture_mode.value,
                document_id=document_id,
            ),
        ) as observation:
            observation.update(
                level="ERROR",
                status_message=summary,
                output={
                    "schema_version": 1,
                    "status": "failed",
                    "summary": summary,
                    "failure_code": failure_code,
                    "attribute_count": len(config.ai_attributes),
                    "group_count": len(groups),
                    "completed_group_count": sum(
                        state.provider_failure_fallback_count == 0
                        for state in states_by_index.values()
                    ),
                    "warning_codes": warning_codes,
                    "groups": group_reports,
                },
                metadata={
                    "resolver": "agentic",
                    "status": "failed",
                    **({"document_id": document_id} if document_id is not None else {}),
                    "failure_code": failure_code,
                },
            )


def _summary_observation_metadata(
    *,
    pipeline_id: str,
    run_id: str,
    step_id: str,
    status: str,
    capture_mode: str,
    document_id: str | None,
) -> dict[str, object]:
    metadata: dict[str, object] = {
        "resolver": "agentic",
        "pipeline_id": pipeline_id,
        "run_id": run_id,
        "step_id": step_id,
        "status": status,
        "capture_mode": capture_mode,
    }
    if document_id is not None:
        metadata["document_id"] = document_id
    return metadata


def _request(
    *,
    group_id: str,
    turn: int,
    attributes: tuple[AgenticAttributeSpec, ...],
    document_view: DocumentView,
    repair: str | None,
    config: AgenticContextResolverConfig,
    pipeline_id: str,
    run_id: str,
    step_id: str,
    user_id: str | None,
) -> AgenticModelRequest:
    return AgenticModelRequest(
        group_id=group_id,
        turn=turn,
        targets=tuple(model_target(attribute) for attribute in attributes),
        document_view=document_view,
        repair_message=repair,
        model_id=config.model_id,
        max_completion_tokens=AGENTIC_MAX_COMPLETION_TOKENS,
        pipeline_id=pipeline_id,
        run_id=run_id,
        step_id=step_id,
        user_id=user_id,
    )


def _attributes_for_issues(
    attributes: tuple[AgenticAttributeSpec, ...],
    issues: tuple[AgenticValidationIssue, ...],
) -> tuple[AgenticAttributeSpec, ...]:
    handles = {issue.handle for issue in issues if issue.handle is not None}
    if any(issue.handle is None for issue in issues) or not handles:
        return attributes
    return tuple(attribute for attribute in attributes if attribute.handle in handles)


def _group_state(
    group_id: str,
    decisions: tuple[ValidatedDecision, ...],
    turns: tuple[AgenticModelTurn, ...],
    *,
    repair_count: int,
    issue_codes: tuple[str, ...],
    coverage_retry_attribute_count: int = 0,
) -> _GroupState:
    return _GroupState(
        group_id=group_id,
        decisions=decisions,
        model_turn_count=len(turns),
        provider_request_count=sum(turn.provider_request_count for turn in turns),
        repair_count=repair_count,
        input_token_count=sum(turn.input_token_count for turn in turns),
        output_token_count=sum(turn.output_token_count for turn in turns),
        truncated_provider_response_count=sum(turn.truncated_response_count for turn in turns),
        finish_reason=_group_finish_reason(turns),
        issue_codes=issue_codes,
        coverage_retry_attribute_count=coverage_retry_attribute_count,
    )


def _timeout_fallback_state(
    *,
    group_id: str,
    attributes: tuple[AgenticAttributeSpec, ...],
    duration_seconds: float = 0.0,
) -> _GroupState:
    return _GroupState(
        group_id=group_id,
        decisions=tuple(
            ValidatedDecision(
                attribute=attribute,
                status="missing",
                value=None,
                evidence=(),
                confidence=0.0,
                model_output_invalid=True,
                requires_review=True,
                diagnostic_codes=("TIME_BUDGET_EXHAUSTED",),
            )
            for attribute in attributes
        ),
        model_turn_count=0,
        provider_request_count=0,
        repair_count=0,
        input_token_count=0,
        output_token_count=0,
        truncated_provider_response_count=0,
        finish_reason=None,
        issue_codes=("TIME_BUDGET_EXHAUSTED",),
        duration_seconds=duration_seconds,
        coverage_retry_attribute_count=0,
        timeout_fallback_count=len(attributes),
    )


def _provider_failure_fallback_state(
    *,
    group_id: str,
    attributes: tuple[AgenticAttributeSpec, ...],
    provider_request_count: int,
) -> _GroupState:
    return _GroupState(
        group_id=group_id,
        decisions=tuple(
            ValidatedDecision(
                attribute=attribute,
                status="missing",
                value=None,
                evidence=(),
                confidence=0.0,
                model_output_invalid=True,
                requires_review=True,
                diagnostic_codes=(_PROVIDER_REQUEST_FAILED,),
            )
            for attribute in attributes
        ),
        model_turn_count=0,
        provider_request_count=provider_request_count,
        repair_count=0,
        input_token_count=0,
        output_token_count=0,
        truncated_provider_response_count=0,
        finish_reason=None,
        issue_codes=(_PROVIDER_REQUEST_FAILED,),
        provider_failure_fallback_count=len(attributes),
    )


def _empty_workflow() -> AgenticWorkflowResult:
    return AgenticWorkflowResult(
        decisions=(),
        group_count=0,
        model_turn_count=0,
        provider_request_count=0,
        tool_round_count=0,
        tool_call_count=0,
        repair_count=0,
        searched_attribute_count=0,
        input_token_count=0,
        output_token_count=0,
        unique_evidence_count=0,
        evidence_reference_count=0,
        repeated_evidence_reference_count=0,
        evidence_char_count=0,
        search_candidate_reference_count=0,
        zero_candidate_attribute_count=0,
        truncated_search_attribute_count=0,
        model_search_term_count=0,
        validation_fallback_missing_attribute_count=0,
        timeout_fallback_missing_attribute_count=0,
        provider_failure_missing_attribute_count=0,
        quote_reference_count=0,
        coverage_pending_attribute_count=0,
        coverage_retry_attribute_count=0,
        truncated_provider_response_count=0,
    )


def _group_report(
    index: int,
    attributes: tuple[AgenticAttributeSpec, ...],
    state: _GroupState,
) -> dict[str, object]:
    fallback_count = sum(decision.model_output_invalid for decision in state.decisions)
    status = (
        "provider_request_failed"
        if state.provider_failure_fallback_count
        else "timeout_fallback"
        if state.timeout_fallback_count
        else "degraded"
        if fallback_count
        else "succeeded_with_warnings"
        if state.issue_codes
        else "succeeded"
    )
    return {
        "group_id": f"G{index:03d}",
        "status": status,
        "handles": [attribute.handle for attribute in attributes],
        "model_turn_count": state.model_turn_count,
        "provider_request_count": state.provider_request_count,
        "repair_count": state.repair_count,
        "coverage_retry_attribute_count": state.coverage_retry_attribute_count,
        "truncated_provider_response_count": state.truncated_provider_response_count,
        "truncated_response_count": state.truncated_provider_response_count,
        "finish_reason": state.finish_reason,
        "duration_seconds": state.duration_seconds,
        "fallback_missing_count": fallback_count,
        "timeout_fallback_missing_count": state.timeout_fallback_count,
        "provider_failure_missing_count": state.provider_failure_fallback_count,
        "issue_codes": list(state.issue_codes),
    }


def _handle_report(index: int, decision: ValidatedDecision) -> dict[str, object]:
    location = _document_location(decision)
    if _PROVIDER_REQUEST_FAILED in decision.diagnostic_codes:
        outcome = "provider_request_failed"
    elif "TIME_BUDGET_EXHAUSTED" in decision.diagnostic_codes:
        outcome = "timeout_fallback"
    elif decision.model_output_invalid:
        outcome = "validation_fallback"
    elif "BUSINESS_MISSING" in decision.diagnostic_codes:
        outcome = "business_missing"
    elif "SECOND_PASS_REQUIRED" in decision.diagnostic_codes:
        outcome = "coverage_pending"
    else:
        outcome = decision.status
    report: dict[str, object] = {
        "handle": decision.attribute.handle,
        "display_name": decision.attribute.display_name,
        "data_type": decision.attribute.data_type,
        "page_number": location[0] if location is not None else None,
        "order_index": location[1] if location is not None else None,
        "group_id": f"G{index:03d}",
        "status": decision.status,
        "outcome": outcome,
        "required": decision.attribute.effective_required,
        "requires_review": decision.requires_review,
        "search_completed": not {
            "TIME_BUDGET_EXHAUSTED",
            _PROVIDER_REQUEST_FAILED,
        }.intersection(decision.diagnostic_codes),
        "candidate_count": decision.candidate_count,
        "evidence_count": len(decision.evidence),
        "derivation": decision.derivation,
        "quote_match_score": decision.quote_match_score,
        "page_hint_missed": decision.page_hint_missed,
        "ambiguous": decision.ambiguous,
        "quote_count": decision.quote_reference_count,
        "confidence": decision.confidence,
        "diagnostic_codes": list(_report_diagnostic_codes(decision)),
    }
    if decision.attribute.constraints:
        report["constraints"] = dict(decision.attribute.constraints)
    if decision.attribute.constraint_warning_codes:
        report["warning_codes"] = list(decision.attribute.constraint_warning_codes)
    return report


def _field_order_report(decisions: tuple[ValidatedDecision, ...]) -> dict[str, object]:
    located: list[tuple[int, int, int, str]] = []
    without_location: list[str] = []
    for index, decision in enumerate(decisions):
        location = _document_location(decision)
        if location is None:
            without_location.append(decision.attribute.display_name)
            continue
        located.append((*location, index, decision.attribute.display_name))
    located.sort(key=lambda item: item[:3])
    return {
        "scope": (
            "Resolver evidence order only; API source mapping and Review ordered-source "
            "filtering are not reflected."
        ),
        "located": [display_name for _, _, _, display_name in located],
        "without_location": without_location,
    }


def _document_location(decision: ValidatedDecision) -> tuple[int, int] | None:
    return min(
        (
            (source.page_number, source.order)
            for source in decision.evidence
            if source.page_number is not None and source.page_number > 0 and source.order >= 0
        ),
        default=None,
    )


def _report_diagnostic_codes(decision: ValidatedDecision) -> tuple[str, ...]:
    codes = list(decision.diagnostic_codes)
    if (
        decision.status == "conflicting"
        and decision.attribute.data_type in _TEXT_CONFLICT_DATA_TYPES
        and decision.candidate_count > _EXCESSIVE_CONFLICT_CANDIDATE_COUNT
    ):
        codes.append("CONFLICT_CANDIDATES_EXCESSIVE")
    return tuple(dict.fromkeys(codes))


def _group_finish_reason(turns: tuple[AgenticModelTurn, ...]) -> str | None:
    reasons = tuple(turn.finish_reason for turn in turns if turn.finish_reason is not None)
    return next(
        (reason for reason in reversed(reasons) if reason != "stop"),
        reasons[-1] if reasons else None,
    )
