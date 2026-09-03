"""App-scoped OCR control-plane maintenance."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable

_LOGGER = logging.getLogger(__name__)


class OcrPipelineRunMaintenance:
    """Run bounded durable-control-plane maintenance until API shutdown."""

    def __init__(self) -> None:
        self._tasks: set[asyncio.Task[None]] = set()
        self._closing = False

    def start_periodic(
        self,
        operation: Callable[[], Awaitable[int]],
        *,
        interval_seconds: float,
        task_name: str,
    ) -> None:
        if self._closing:
            raise RuntimeError("OCR pipeline maintenance is shutting down.")
        task = asyncio.create_task(
            self._periodic(operation, interval_seconds=interval_seconds),
            name=task_name,
        )
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def shutdown(self) -> None:
        self._closing = True
        tasks = tuple(self._tasks)
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _periodic(
        self,
        operation: Callable[[], Awaitable[int]],
        *,
        interval_seconds: float,
    ) -> None:
        while not self._closing:
            try:
                await operation()
            except asyncio.CancelledError:
                raise
            except Exception:
                _LOGGER.exception("OCR pipeline periodic maintenance failed.")
            try:
                await asyncio.wait_for(asyncio.Event().wait(), timeout=interval_seconds)
            except TimeoutError:
                continue
