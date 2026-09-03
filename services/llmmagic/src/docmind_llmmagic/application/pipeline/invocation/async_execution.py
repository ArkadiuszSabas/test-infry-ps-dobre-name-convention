"""Admission and bounded in-process execution for internal OCR runs."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import StrEnum
from threading import Lock

from docmind_llmmagic.application.pipeline.invocation.contracts import PipelineTraceContext
from docmind_llmmagic.application.pipeline.invocation.service import (
    PipelineInvocationCommand,
    PipelineInvocationResult,
    PipelineInvocationService,
)
from docmind_llmmagic.domain.pipeline.models import PipelineProgress, PipelineStatus, StepError

_LOGGER = logging.getLogger("docmind_llmmagic.ocr_execution")


class AdmissionDisposition(StrEnum):
    ACCEPTED = "accepted"
    DUPLICATE = "duplicate"


class AdmissionError(Exception):
    """Expected admission rejection with an HTTP-compatible status."""

    def __init__(self, code: str, message: str, status_code: int) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class StaleCompletionError(RuntimeError):
    """The API rejected completion as stale; do not retry it."""


class RetryableCompletionError(RuntimeError):
    """A transient completion failure eligible for the bounded retry policy."""


@dataclass(frozen=True, slots=True)
class RunKey:
    run_id: str
    attempt_id: str
    fencing_token: int = 0


class InMemoryOcrRunRegistry:
    """Thread-safe registry of admitted whole-pipeline executions for one replica."""

    def __init__(self, *, max_concurrency: int = 1) -> None:
        if max_concurrency < 1:
            raise ValueError("max_concurrency must be positive")
        self._execution_concurrency = max_concurrency
        self._registered: set[RunKey] = set()
        self._lock = Lock()

    def admit(self, key: RunKey) -> AdmissionDisposition:
        with self._lock:
            if key in self._registered:
                return AdmissionDisposition.DUPLICATE
            if any(registered.run_id == key.run_id for registered in self._registered):
                raise AdmissionError("OCR_CAPACITY_EXHAUSTED", "OCR capacity is exhausted.", 429)
            if len(self._registered) >= self._execution_concurrency:
                raise AdmissionError("OCR_CAPACITY_EXHAUSTED", "OCR capacity is exhausted.", 429)
            self._registered.add(key)
            return AdmissionDisposition.ACCEPTED

    def release(self, key: RunKey) -> None:
        with self._lock:
            self._registered.discard(key)

    def contains(self, key: RunKey) -> bool:
        with self._lock:
            return key in self._registered

    @property
    def registered_count(self) -> int:
        with self._lock:
            return len(self._registered)

    @property
    def execution_concurrency(self) -> int:
        return self._execution_concurrency


ProgressPublisher = Callable[
    [RunKey, PipelineProgress, int, str | None, PipelineTraceContext], Awaitable[None] | None
]
CompletionPublisher = Callable[
    [RunKey, PipelineInvocationResult, PipelineTraceContext], Awaitable[bool]
]
TerminalPublisher = Callable[
    [RunKey, PipelineInvocationResult, int, PipelineTraceContext], Awaitable[None] | None
]
CancellationPublisher = Callable[[RunKey, str, str, int, str], Awaitable[None]]


@dataclass(slots=True)
class _ExecutionEntry:
    task: asyncio.Task[None]
    command: PipelineInvocationCommand
    last_sequence: int = 0


class AsyncOcrExecutionService:
    """Admit quickly, execute with the existing runner, and report safe outcomes."""

    def __init__(
        self,
        invocation_service: PipelineInvocationService,
        registry: InMemoryOcrRunRegistry,
        *,
        progress_publisher: ProgressPublisher | None = None,
        completion_publisher: CompletionPublisher | None = None,
        terminal_publisher: TerminalPublisher | None = None,
        cancellation_publisher: CancellationPublisher | None = None,
    ) -> None:
        self._invocation_service = invocation_service
        self._registry = registry
        self._progress_publisher = progress_publisher
        self._completion_publisher = completion_publisher
        self._terminal_publisher = terminal_publisher
        self._cancellation_publisher = cancellation_publisher
        self._tasks: dict[RunKey, _ExecutionEntry] = {}
        self._cancelled: set[RunKey] = set()

    def admit(
        self,
        key: RunKey,
        command: PipelineInvocationCommand,
        *,
        definition: object,
    ) -> AdmissionDisposition:
        if key in self._cancelled:
            return AdmissionDisposition.DUPLICATE
        disposition = self._registry.admit(key)
        if disposition is AdmissionDisposition.DUPLICATE:
            return disposition
        task = asyncio.create_task(self.execute(key, command, definition))
        self._tasks[key] = _ExecutionEntry(task=task, command=command)
        task.add_done_callback(lambda completed: self._forget_task(key, completed))
        return disposition

    def cancel(
        self,
        key: RunKey,
        *,
        document_id: str,
        pipeline_id: str,
        next_event_sequence: int,
        correlation_id: str,
    ) -> bool:
        """Request cancellation of one exact active run/attempt/fence."""

        self._cancelled.add(key)
        entry = self._tasks.get(key)
        if entry is None:
            reporter = asyncio.create_task(
                self._report_inactive_cancellation(
                    key,
                    document_id=document_id,
                    pipeline_id=pipeline_id,
                    next_event_sequence=next_event_sequence,
                    correlation_id=correlation_id,
                )
            )
            reporter.add_done_callback(self._consume_task_exception)
            return False
        entry.task.cancel()
        reporter = asyncio.create_task(
            self._report_cancellation(
                key,
                entry,
                document_id=document_id,
                pipeline_id=pipeline_id,
                next_event_sequence=next_event_sequence,
                correlation_id=correlation_id,
            )
        )
        reporter.add_done_callback(self._consume_task_exception)
        return True

    @property
    def invocation_service(self) -> PipelineInvocationService:
        """Return the runner service owned by this executor."""

        return self._invocation_service

    async def execute(
        self,
        key: RunKey,
        command: PipelineInvocationCommand,
        definition: object,
    ) -> None:
        """Run an already-admitted pipeline and release its registration."""

        try:
            await self._execute_admitted(key, command, definition)
        finally:
            self._registry.release(key)

    async def _execute_admitted(
        self,
        key: RunKey,
        command: PipelineInvocationCommand,
        definition: object,
    ) -> None:
        result: PipelineInvocationResult | None = None
        sequence = 0
        try:
            previous_completed: frozenset[str] = frozenset()
            started_published = False

            async def publish_progress(progress: PipelineProgress) -> None:
                nonlocal sequence, previous_completed, started_published
                newly_completed = tuple(
                    step.step_id
                    for step in progress.steps
                    if step.status.value in {"succeeded", "failed", "skipped"}
                    and step.step_id not in previous_completed
                )
                previous_completed = previous_completed.union(newly_completed)
                progress_publisher = self._progress_publisher
                if progress_publisher is None:
                    return

                async def publish_one(completed_step_id: str | None) -> None:
                    nonlocal sequence
                    sequence += 1
                    entry = self._tasks.get(key)
                    if entry is not None:
                        entry.last_sequence = sequence
                    if command.trace_context is None:
                        return
                    is_started_event = sequence == 1 and completed_step_id is None
                    delays = (0, 1, 2) if is_started_event else (0,)
                    for attempt, delay in enumerate(delays, start=1):
                        if delay:
                            await asyncio.sleep(delay)
                        try:
                            publication = progress_publisher(
                                key,
                                progress,
                                sequence,
                                completed_step_id,
                                command.trace_context,
                            )
                            if publication is not None:
                                await publication
                            return
                        except Exception:
                            if is_started_event and attempt < len(delays):
                                continue
                            if is_started_event:
                                raise
                            _LOGGER.warning(
                                "OCR progress publication failed.",
                                extra={"run_id": key.run_id},
                            )

                if not started_published:
                    started_published = True
                    await publish_one(None)
                for completed_step_id in newly_completed:
                    await publish_one(completed_step_id)

            result = await self._invocation_service.invoke_compiled_definition(
                command,
                definition=definition,  # type: ignore[arg-type]
                progress_callback=publish_progress,
            )
        except Exception:
            _LOGGER.error("OCR execution failed.", extra={"run_id": key.run_id})
            result = PipelineInvocationResult(
                pipeline_id=command.pipeline_id,
                run_id=command.run_id or key.run_id,
                status=PipelineStatus.FAILED,
                trace=(),
                error=StepError(
                    code="PIPELINE_EXECUTION_FAILED",
                    message="Pipeline execution failed.",
                ),
            )
        finally:
            if (
                result is not None
                and self._completion_publisher is not None
                and command.trace_context is not None
            ):
                completed = await self.complete_with_retries(key, result, command.trace_context)
                if completed and self._terminal_publisher is not None:
                    terminal = self._terminal_publisher(
                        key, result, sequence + 1, command.trace_context
                    )
                    if terminal is not None:
                        try:
                            await terminal
                        except Exception:
                            _LOGGER.warning(
                                "OCR terminal publication failed.", extra={"run_id": key.run_id}
                            )

    async def complete_with_retries(
        self,
        key: RunKey,
        result: PipelineInvocationResult,
        trace_context: PipelineTraceContext,
    ) -> bool:
        for attempt, delay in enumerate((0, 1, 2), start=1):
            if delay:
                await asyncio.sleep(delay)
            try:
                if await self._completion_publisher(key, result, trace_context):  # type: ignore[misc]
                    return True
                return False
            except StaleCompletionError:
                return False
            except RetryableCompletionError:
                if attempt == 3:
                    _LOGGER.warning(
                        "OCR completion failed after retries.", extra={"run_id": key.run_id}
                    )
            except Exception:
                _LOGGER.warning(
                    "OCR completion failed without retry.", extra={"run_id": key.run_id}
                )
                return False
        return False

    @staticmethod
    def _consume_task_exception(task: asyncio.Task[None]) -> None:
        try:
            task.exception()
        except asyncio.CancelledError:
            pass

    def _forget_task(self, key: RunKey, task: asyncio.Task[None]) -> None:
        current = self._tasks.get(key)
        if current is not None and current.task is task:
            self._tasks.pop(key, None)
        self._consume_task_exception(task)

    async def _report_cancellation(
        self,
        key: RunKey,
        entry: _ExecutionEntry,
        *,
        document_id: str,
        pipeline_id: str,
        next_event_sequence: int,
        correlation_id: str,
    ) -> None:
        try:
            await entry.task
        except asyncio.CancelledError:
            pass
        publisher = self._cancellation_publisher
        if publisher is not None:
            await publisher(
                key,
                document_id,
                pipeline_id,
                max(next_event_sequence, entry.last_sequence + 1),
                correlation_id,
            )

    async def _report_inactive_cancellation(
        self,
        key: RunKey,
        *,
        document_id: str,
        pipeline_id: str,
        next_event_sequence: int,
        correlation_id: str,
    ) -> None:
        publisher = self._cancellation_publisher
        if publisher is not None:
            await publisher(
                key,
                document_id,
                pipeline_id,
                next_event_sequence,
                correlation_id,
            )
