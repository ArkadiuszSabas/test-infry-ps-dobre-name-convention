"""App-scoped scheduling for direct OCR pipeline runs."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from uuid import UUID

from docmind_api.application.ocr_pipeline_runs.ports import OcrPipelineRunDispatch

_LOGGER = logging.getLogger(__name__)


class OcrPipelineRunTaskScheduler:
    """Run direct OCR dispatches independently from HTTP request resources."""

    def __init__(self, *, max_concurrency: int) -> None:
        if max_concurrency < 1:
            raise ValueError("OCR pipeline run concurrency must be positive.")
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._tasks: set[asyncio.Task[None]] = set()
        self._closing = False

    def schedule(self, dispatch: OcrPipelineRunDispatch, run_id: UUID) -> None:
        """Schedule one committed run without extending its originating request."""

        if self._closing:
            raise RuntimeError("OCR pipeline run scheduler is shutting down.")
        task = asyncio.create_task(
            self._run(dispatch, run_id),
            name=f"ocr-pipeline-run-{run_id}",
        )
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    def start_watchdog(
        self,
        reconcile: Callable[[], Awaitable[int]],
        *,
        interval_seconds: float,
    ) -> None:
        """Run a bounded stale-execution reconciliation loop for this API replica."""

        if self._closing:
            raise RuntimeError("OCR pipeline run scheduler is shutting down.")
        task = asyncio.create_task(
            self._watch(reconcile, interval_seconds=interval_seconds),
            name="ocr-pipeline-run-watchdog",
        )
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def shutdown(self) -> None:
        """Cancel and observe active dispatches before app-owned resources close."""

        self._closing = True
        tasks = tuple(self._tasks)
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _run(self, dispatch: OcrPipelineRunDispatch, run_id: UUID) -> None:
        try:
            async with self._semaphore:
                await dispatch(run_id)
        except asyncio.CancelledError:
            raise
        except Exception:
            _LOGGER.exception(
                "OCR pipeline run background dispatch failed.",
                extra={"ocr_pipeline_run_id": str(run_id)},
            )

    async def _watch(
        self,
        reconcile: Callable[[], Awaitable[int]],
        *,
        interval_seconds: float,
    ) -> None:
        while not self._closing:
            try:
                await asyncio.sleep(interval_seconds)
            except asyncio.CancelledError:
                raise
            if self._closing:
                return
            try:
                failed_count = await reconcile()
                if failed_count:
                    _LOGGER.warning(
                        "OCR pipeline watchdog failed abandoned runs.",
                        extra={"ocr_pipeline_run_failed_count": failed_count},
                    )
            except asyncio.CancelledError:
                raise
            except Exception:
                _LOGGER.exception("OCR pipeline watchdog reconciliation failed.")
