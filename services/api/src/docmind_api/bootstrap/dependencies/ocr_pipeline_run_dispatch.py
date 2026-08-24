"""Lease-aware direct OCR pipeline dispatch wiring."""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import replace
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from docmind_api.application.document_review.service import DocumentReviewService
from docmind_api.application.ocr_pipeline_runs.errors import (
    OcrPipelineRunInvocationIndeterminateError,
    OcrPipelineRunLlmMagicUnavailableError,
)
from docmind_api.application.ocr_pipeline_runs.execution import OcrPipelineRunExecutionService
from docmind_api.application.ocr_pipeline_runs.ports import (
    OcrPipelineRunExecutionPolicy,
    OcrPipelineRunInvocationContext,
)
from docmind_api.domain.ocr_pipeline_runs.models import (
    OcrPipelineRunAcquireDisposition,
    OcrPipelineRunAcquireReason,
    OcrPipelineRunExecutionLease,
    OcrPipelineRunRecord,
)
from docmind_api.infrastructure.document_review.context_resolution_source import (
    SqlAlchemyDocumentReviewPipelineSource,
)
from docmind_api.infrastructure.document_review.providers import (
    UnavailableDocumentReviewProvider,
)
from docmind_api.infrastructure.ocr_pipeline_runs.llmmagic_dapr import (
    DaprLlmMagicOcrPipelineRunInvoker,
)
from docmind_api.infrastructure.ocr_pipeline_runs.runtime import (
    UtcClock,
    UuidOcrPipelineRunExecutionIdentityFactory,
)
from docmind_api.infrastructure.persistence.document_review.approval_settings_repository import (
    SqlAlchemyDocumentApprovalSettingsRepository,
)
from docmind_api.infrastructure.persistence.document_review.repositories import (
    SqlAlchemyDocumentApprovalWorkflowRepository,
    SqlAlchemyDocumentReviewRepository,
)
from docmind_api.infrastructure.persistence.documents.repositories import (
    SqlAlchemyDocumentRegistryRepository,
)
from docmind_api.infrastructure.persistence.ocr_pipeline_runs.repositories import (
    SqlAlchemyOcrPipelineRunRepository,
)
from docmind_api.infrastructure.persistence.sql import database_session_scope
from docmind_api.settings import get_dapr_client_settings
from docmind_backend_runtime import create_dapr_client

_LOGGER = logging.getLogger(__name__)


class _LazyDaprLlmMagicOcrPipelineRunInvoker:
    """Build the Dapr client inside the invocation failure boundary."""

    def __init__(self, *, timeout_seconds: float) -> None:
        self._timeout_seconds = timeout_seconds

    async def invoke_run(
        self,
        record: OcrPipelineRunRecord,
        context: OcrPipelineRunInvocationContext,
    ) -> OcrPipelineRunRecord:
        try:
            dapr_settings = replace(
                get_dapr_client_settings(),
                timeout_seconds=self._timeout_seconds,
            )
            dapr_client = create_dapr_client(dapr_settings)
        except Exception as error:
            raise OcrPipelineRunLlmMagicUnavailableError() from error

        return await DaprLlmMagicOcrPipelineRunInvoker(dapr_client=dapr_client).invoke_run(
            record,
            context,
        )


class DirectOcrPipelineRunDispatcher:
    """Execute direct OCR runs with PostgreSQL-backed lease and fencing."""

    def __init__(
        self,
        *,
        session_factory: async_sessionmaker[AsyncSession],
        invocation_timeout_seconds: float,
        execution_policy: OcrPipelineRunExecutionPolicy,
    ) -> None:
        self._session_factory = session_factory
        self._invocation_timeout_seconds = invocation_timeout_seconds
        self._execution_policy = execution_policy

    async def dispatch(self, run_id: UUID) -> None:
        """Acquire, invoke, heartbeat, and finalize one logical run."""

        acquired = await self._acquire(run_id)
        if acquired.disposition == OcrPipelineRunAcquireDisposition.ACTIVE_DUPLICATE:
            _log_event("active_duplicate", run_id)
            return
        if acquired.disposition == OcrPipelineRunAcquireDisposition.RESULT_REUSED:
            _log_event("result_reused", run_id)
            await self._initialize_review(acquired.record.document_id, acquired.record.id)
            return
        if acquired.disposition == OcrPipelineRunAcquireDisposition.RETRY_EXHAUSTED:
            _log_event("retry_exhausted", run_id, level=logging.WARNING)
            return
        if acquired.disposition == OcrPipelineRunAcquireDisposition.AMBIGUOUS:
            _log_event("ambiguous_ownership", run_id, level=logging.ERROR)
            return

        lease = acquired.lease
        reason = acquired.reason
        if lease is None or reason is None:
            raise RuntimeError("Acquired OCR pipeline execution is missing its lease.")
        _log_acquisition(reason, lease)

        stop_heartbeat = asyncio.Event()
        ownership_lost = asyncio.Event()
        heartbeat = asyncio.create_task(
            self._heartbeat(lease, stop_heartbeat, ownership_lost),
            name=f"ocr-pipeline-run-heartbeat-{lease.attempt_id}",
        )
        invocation_started = False
        try:
            marked = await self._mark_invocation_started(lease)
            if not marked:
                _log_event(
                    "fenced_write_rejected",
                    run_id,
                    lease=lease,
                    level=logging.WARNING,
                )
                return
            invocation_started = True
            completed = await self._invoke(acquired.record, lease, reason)

            if ownership_lost.is_set():
                _log_event("ownership_lost", run_id, lease=lease, level=logging.WARNING)
                return
            saved = await self._save_result(lease, completed)
            if not saved:
                _log_event(
                    "fenced_write_rejected",
                    run_id,
                    lease=lease,
                    level=logging.WARNING,
                )
                return
        except OcrPipelineRunInvocationIndeterminateError:
            await self._try_record_indeterminate(
                lease,
                event="invocation_timeout_indeterminate",
                record=self._record_indeterminate_timeout,
            )
            return
        except asyncio.CancelledError:
            if invocation_started:
                await asyncio.shield(
                    self._try_record_indeterminate(
                        lease,
                        event="invocation_cancelled_indeterminate",
                        record=self._record_indeterminate_cancellation,
                    )
                )
            raise
        finally:
            stop_heartbeat.set()
            await heartbeat

        await self._initialize_review(completed.document_id, completed.id)

    async def fail_stale_executions(self, *, stale_after_seconds: float) -> int:
        """Fail abandoned executions through the fenced persistence boundary."""

        async with database_session_scope(self._session_factory) as session:
            return await self._execution_service(session).fail_stale_executions(
                stale_after_seconds=stale_after_seconds,
            )

    async def _acquire(self, run_id: UUID):
        async with database_session_scope(self._session_factory) as session:
            return await self._execution_service(session).acquire(run_id)

    async def _invoke(
        self,
        record: OcrPipelineRunRecord,
        lease: OcrPipelineRunExecutionLease,
        reason: OcrPipelineRunAcquireReason,
    ) -> OcrPipelineRunRecord:
        async with self._session_factory() as session:
            return await self._execution_service(
                session,
                invoker=_LazyDaprLlmMagicOcrPipelineRunInvoker(
                    timeout_seconds=self._invocation_timeout_seconds,
                ),
            ).invoke(
                record,
                OcrPipelineRunInvocationContext(
                    attempt_id=lease.attempt_id,
                    attempt_number=lease.attempt_number,
                    fencing_token=lease.fencing_token,
                    acquisition_reason=reason,
                ),
            )

    async def _save_result(
        self,
        lease: OcrPipelineRunExecutionLease,
        record: OcrPipelineRunRecord,
    ) -> bool:
        async with database_session_scope(self._session_factory) as session:
            return await self._execution_service(session).save_result(lease, record)

    async def _mark_invocation_started(
        self,
        lease: OcrPipelineRunExecutionLease,
    ) -> bool:
        async with database_session_scope(self._session_factory) as session:
            return await self._execution_service(session).mark_invocation_started(lease)

    async def _record_indeterminate_timeout(
        self,
        lease: OcrPipelineRunExecutionLease,
    ) -> bool:
        async with database_session_scope(self._session_factory) as session:
            return await self._execution_service(session).record_indeterminate_timeout(lease)

    async def _record_indeterminate_cancellation(
        self,
        lease: OcrPipelineRunExecutionLease,
    ) -> bool:
        async with database_session_scope(self._session_factory) as session:
            return await self._execution_service(session).record_indeterminate_cancellation(lease)

    async def _try_record_indeterminate(
        self,
        lease: OcrPipelineRunExecutionLease,
        *,
        event: str,
        record: Callable[[OcrPipelineRunExecutionLease], Awaitable[bool]],
    ) -> None:
        try:
            recorded = await record(lease)
        except Exception:
            _LOGGER.exception(
                "OCR pipeline indeterminate marker persistence failed; "
                "the invocation-started fence remains fail-closed.",
                extra={
                    "ocr_pipeline_run_id": str(lease.run_id),
                    "ocr_pipeline_attempt_id": str(lease.attempt_id),
                    "fencing_token": lease.fencing_token,
                },
            )
        else:
            if not recorded:
                _log_event(
                    "fenced_write_rejected",
                    lease.run_id,
                    lease=lease,
                    level=logging.WARNING,
                )
        _log_event(event, lease.run_id, lease=lease, level=logging.WARNING)

    async def _heartbeat(
        self,
        initial_lease: OcrPipelineRunExecutionLease,
        stop: asyncio.Event,
        ownership_lost: asyncio.Event,
    ) -> None:
        lease = initial_lease
        while not stop.is_set():
            try:
                await asyncio.wait_for(
                    stop.wait(),
                    timeout=self._execution_policy.lease_renewal_interval_seconds,
                )
                return
            except TimeoutError:
                pass

            try:
                async with database_session_scope(self._session_factory) as session:
                    renewed = await self._execution_service(session).renew(lease)
            except Exception:
                _LOGGER.exception(
                    "OCR pipeline execution lease renewal failed.",
                    extra={
                        "ocr_pipeline_run_id": str(lease.run_id),
                        "ocr_pipeline_attempt_id": str(lease.attempt_id),
                        "fencing_token": lease.fencing_token,
                    },
                )
                continue

            if renewed is None:
                ownership_lost.set()
                return
            lease = renewed

    def _execution_service(
        self,
        session: AsyncSession,
        *,
        invoker: _LazyDaprLlmMagicOcrPipelineRunInvoker | None = None,
    ) -> OcrPipelineRunExecutionService:
        from docmind_api.infrastructure.ocr_pipeline_runs.runtime import (
            UnavailableOcrPipelineRunInvoker,
        )

        return OcrPipelineRunExecutionService(
            repository=SqlAlchemyOcrPipelineRunRepository(session),
            invoker=invoker or UnavailableOcrPipelineRunInvoker(),
            identity_factory=UuidOcrPipelineRunExecutionIdentityFactory(),
            clock=UtcClock(),
            policy=self._execution_policy,
        )

    async def _initialize_review(self, document_id: UUID, run_id: UUID) -> None:
        async with database_session_scope(self._session_factory) as session:
            document_repository = SqlAlchemyDocumentRegistryRepository(session)
            service = DocumentReviewService(
                provider=UnavailableDocumentReviewProvider(
                    document_repository=document_repository,
                ),
                repository=SqlAlchemyDocumentReviewRepository(session),
                pipeline_source=SqlAlchemyDocumentReviewPipelineSource(session),
                approval_repository=SqlAlchemyDocumentApprovalWorkflowRepository(session),
                approval_settings_repository=SqlAlchemyDocumentApprovalSettingsRepository(session),
                document_repository=document_repository,
            )
            replaced = await service.replace_reprocessing_review_from_pipeline_run(
                document_id,
                run_id,
            )
            if not replaced:
                await service.initialize_from_first_pipeline_result(document_id)


def _log_acquisition(
    reason: OcrPipelineRunAcquireReason,
    lease: OcrPipelineRunExecutionLease,
) -> None:
    event = {
        OcrPipelineRunAcquireReason.NEW: "execution_acquired",
        OcrPipelineRunAcquireReason.RETRY: "retry_acquired",
        OcrPipelineRunAcquireReason.EXPIRED_LEASE_TAKEOVER: "expired_lease_takeover",
    }[reason]
    _log_event(event, lease.run_id, lease=lease)


def _log_event(
    event: str,
    run_id: UUID,
    *,
    lease: OcrPipelineRunExecutionLease | None = None,
    level: int = logging.INFO,
) -> None:
    extra: dict[str, object] = {
        "ocr_pipeline_execution_event": event,
        "ocr_pipeline_execution_metric": f"ocr_pipeline_execution.{event}",
        "ocr_pipeline_execution_metric_value": 1,
        "ocr_pipeline_run_id": str(run_id),
    }
    if lease is not None:
        extra.update(
            {
                "ocr_pipeline_attempt_id": str(lease.attempt_id),
                "fencing_token": lease.fencing_token,
            }
        )
    _LOGGER.log(level, "OCR pipeline execution event.", extra=extra)
