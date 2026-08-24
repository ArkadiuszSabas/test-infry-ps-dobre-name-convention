"""Lease-aware orchestration for physical OCR pipeline executions."""

import logging
from dataclasses import replace
from datetime import datetime, timedelta
from types import TracebackType
from uuid import UUID

from docmind_api.application.ocr_pipeline_runs.errors import (
    OcrPipelineRunInvocationIndeterminateError,
    OcrPipelineRunLlmMagicUnavailableError,
    OcrPipelineRunNotFoundError,
)
from docmind_api.application.ocr_pipeline_runs.ports import (
    Clock,
    OcrPipelineRunExecutionIdentityFactory,
    OcrPipelineRunExecutionPolicy,
    OcrPipelineRunInvocationContext,
    OcrPipelineRunInvoker,
    OcrPipelineRunRepository,
)
from docmind_api.domain.ocr_pipeline_runs.models import (
    OcrPipelineRunAcquireResult,
    OcrPipelineRunDiagnostic,
    OcrPipelineRunDiagnosticSeverity,
    OcrPipelineRunError,
    OcrPipelineRunExecutionLease,
    OcrPipelineRunRecord,
    OcrPipelineRunStatus,
)

_LOGGER = logging.getLogger(__name__)


class OcrPipelineRunExecutionService:
    """Application boundary for acquiring, invoking, renewing, and fencing runs."""

    def __init__(
        self,
        *,
        repository: OcrPipelineRunRepository,
        invoker: OcrPipelineRunInvoker,
        identity_factory: OcrPipelineRunExecutionIdentityFactory,
        clock: Clock,
        policy: OcrPipelineRunExecutionPolicy,
    ) -> None:
        self._repository = repository
        self._invoker = invoker
        self._identity_factory = identity_factory
        self._clock = clock
        self._policy = policy

    async def acquire(self, run_id: UUID | str) -> OcrPipelineRunAcquireResult:
        """Atomically acquire execution ownership or return the current outcome."""

        acquired_at = self._clock.now()
        result = await self._repository.acquire_execution(
            run_id,
            attempt_id=self._identity_factory.new_attempt_id(),
            owner_token=self._identity_factory.new_owner_token(),
            acquired_at=acquired_at,
            lease_expires_at=acquired_at + timedelta(seconds=self._policy.lease_duration_seconds),
            max_attempts=self._policy.max_attempts,
        )
        if result is None:
            raise OcrPipelineRunNotFoundError(run_id=run_id)
        return result

    async def renew(
        self,
        lease: OcrPipelineRunExecutionLease,
    ) -> OcrPipelineRunExecutionLease | None:
        """Renew ownership without allowing an expired owner to recover."""

        renewed_at = self._clock.now()
        return await self._repository.renew_execution(
            lease,
            renewed_at=renewed_at,
            lease_expires_at=renewed_at + timedelta(seconds=self._policy.lease_duration_seconds),
        )

    async def invoke(
        self,
        record: OcrPipelineRunRecord,
        context: OcrPipelineRunInvocationContext,
    ) -> OcrPipelineRunRecord:
        """Invoke the pipeline and map only determinate failures to terminal state."""

        try:
            invoked = await self._invoker.invoke_run(record, context)
            completed_at = self._clock.now()
            return replace(invoked, completed_at=completed_at, updated_at=completed_at)
        except OcrPipelineRunInvocationIndeterminateError:
            _LOGGER.warning(
                "OCR pipeline invocation outcome is indeterminate; lease will expire naturally.",
                extra={"ocr_pipeline_run_id": str(record.id)},
            )
            raise
        except OcrPipelineRunLlmMagicUnavailableError as error:
            _LOGGER.exception(
                "LLM Magic OCR pipeline run invocation is unavailable.",
                exc_info=_safe_exc_info(error),
                extra={
                    "ocr_pipeline_run_id": str(record.id),
                    "pipeline_id": str(record.pipeline_id),
                    "error_type": type(error).__name__,
                },
            )
            return _failed_run(
                record,
                code="LLMMAGIC_RUN_UNAVAILABLE",
                message="LLM Magic OCR pipeline run service is unavailable.",
                completed_at=self._clock.now(),
            )
        except Exception as error:
            _LOGGER.exception(
                "Unexpected OCR pipeline run invocation failure.",
                exc_info=_safe_exc_info(error),
                extra={
                    "ocr_pipeline_run_id": str(record.id),
                    "pipeline_id": str(record.pipeline_id),
                    "error_type": type(error).__name__,
                },
            )
            return _failed_run(
                record,
                code="OCR_PIPELINE_RUN_FAILED",
                message="OCR pipeline run failed.",
                completed_at=self._clock.now(),
            )

    async def mark_invocation_started(
        self,
        lease: OcrPipelineRunExecutionLease,
    ) -> bool:
        """Persist the no-takeover boundary before calling LLM Magic."""

        return await self._repository.mark_execution_invocation_started(lease)

    async def save_result(
        self,
        lease: OcrPipelineRunExecutionLease,
        record: OcrPipelineRunRecord,
    ) -> bool:
        """Persist a terminal result through the current fencing token."""

        completed_at = self._clock.now()
        return await self._repository.save_execution_result(
            lease,
            record,
            completed_at=completed_at,
        )

    async def record_indeterminate_timeout(
        self,
        lease: OcrPipelineRunExecutionLease,
    ) -> bool:
        """Record a safe timeout marker without declaring execution finished."""

        return await self._repository.record_execution_error(
            lease,
            error_code="OCR_PIPELINE_RUN_INVOCATION_TIMEOUT_INDETERMINATE",
            updated_at=self._clock.now(),
        )

    async def record_indeterminate_cancellation(
        self,
        lease: OcrPipelineRunExecutionLease,
    ) -> bool:
        """Record an interrupted invocation without allowing automatic takeover."""

        return await self._repository.record_execution_error(
            lease,
            error_code="OCR_PIPELINE_RUN_INVOCATION_CANCELLED_INDETERMINATE",
            updated_at=self._clock.now(),
        )

    async def fail_stale_executions(self, *, stale_after_seconds: float) -> int:
        """Terminally fail abandoned runs after the configured recovery deadline."""

        return await self._repository.fail_stale_executions(
            stale_after_seconds=stale_after_seconds,
        )


def _failed_run(
    record: OcrPipelineRunRecord,
    *,
    code: str,
    message: str,
    completed_at: datetime,
) -> OcrPipelineRunRecord:
    return replace(
        record,
        status=OcrPipelineRunStatus.FAILED,
        diagnostics=(
            *record.diagnostics,
            OcrPipelineRunDiagnostic(
                severity=OcrPipelineRunDiagnosticSeverity.ERROR,
                code=code,
                message=message,
            ),
        ),
        error=OcrPipelineRunError(code=code, message=message),
        completed_at=completed_at,
        updated_at=completed_at,
    )


def _safe_exc_info(
    error: Exception,
) -> tuple[type[RuntimeError], RuntimeError, TracebackType | None]:
    return (
        RuntimeError,
        RuntimeError(type(error).__name__),
        error.__traceback__,
    )
