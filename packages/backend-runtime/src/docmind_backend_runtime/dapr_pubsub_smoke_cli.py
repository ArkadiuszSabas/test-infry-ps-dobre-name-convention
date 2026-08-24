"""Terminal CLI for the local Dapr pub/sub smoke check."""

from __future__ import annotations

import argparse
import asyncio
from collections.abc import Callable, Coroutine, Sequence
from dataclasses import dataclass
from os import environ
from sys import stdout
from time import perf_counter
from typing import Any, TextIO

import httpx

from docmind_backend_runtime.dapr_pubsub_smoke import (
    DaprPubSubSmokeStepResult,
    publish_dapr_pubsub_smoke_event,
    wait_for_dapr_pubsub_smoke_consumption,
)
from docmind_backend_runtime.dapr_pubsub_smoke_contracts import (
    DAPR_PUBSUB_SMOKE_PUBSUB_NAME,
    DAPR_PUBSUB_SMOKE_TOPIC,
    DEFAULT_PUBSUB_SMOKE_API_BASE_URL,
    DEFAULT_PUBSUB_SMOKE_CORRELATION_ID,
    DEFAULT_PUBSUB_SMOKE_MESSAGE,
    DEFAULT_PUBSUB_SMOKE_WORKER_BASE_URL,
    DaprPubSubSmokeEvent,
    new_dapr_pubsub_smoke_operation_id,
)

_API_BASE_URL_ENV = "DOCMIND_API_BASE_URL"
_WORKER_BASE_URL_ENV = "DOCMIND_WORKER_BASE_URL"
_CORRELATION_ID_ENV = "DOCMIND_DAPR_PUBSUB_SMOKE_CORRELATION_ID"
_DEFAULT_PROGRESS_INTERVAL_SECONDS = 0.25
_DEFAULT_TIMEOUT_SECONDS = 10.0


@dataclass(frozen=True, slots=True)
class _CliArgs:
    api_base_url: str
    worker_base_url: str
    operation_id: str
    correlation_id: str
    message: str
    timeout_seconds: float
    progress_interval_seconds: float
    no_color: bool


@dataclass(frozen=True, slots=True)
class _Palette:
    enabled: bool

    def heading(self, value: str) -> str:
        return self._style(value, "1")

    def ok(self, value: str) -> str:
        return self._style(value, "32")

    def fail(self, value: str) -> str:
        return self._style(value, "31")

    def _style(self, value: str, code: str) -> str:
        if not self.enabled:
            return value

        return f"\033[{code}m{value}\033[0m"


def main(argv: Sequence[str] | None = None) -> int:
    """Run the Dapr pub/sub smoke CLI."""

    args = _parse_args(argv)
    try:
        return asyncio.run(
            run_local_dapr_pubsub_smoke_cli(
                api_base_url=args.api_base_url,
                worker_base_url=args.worker_base_url,
                operation_id=args.operation_id,
                correlation_id=args.correlation_id,
                message=args.message,
                timeout_seconds=args.timeout_seconds,
                progress_interval_seconds=args.progress_interval_seconds,
                color_enabled=not args.no_color and "NO_COLOR" not in environ,
                output=stdout,
            ),
        )
    except KeyboardInterrupt:
        stdout.write("\nDapr pub/sub smoke interrupted.\n")
        return 130


async def run_local_dapr_pubsub_smoke_cli(
    *,
    api_base_url: str,
    worker_base_url: str,
    operation_id: str,
    correlation_id: str,
    message: str = DEFAULT_PUBSUB_SMOKE_MESSAGE,
    timeout_seconds: float = _DEFAULT_TIMEOUT_SECONDS,
    progress_interval_seconds: float = _DEFAULT_PROGRESS_INTERVAL_SECONDS,
    color_enabled: bool = True,
    output: TextIO = stdout,
    http_client: httpx.AsyncClient | None = None,
) -> int:
    """Run the local DocMind Dapr pub/sub smoke with human-oriented progress output."""

    palette = _Palette(enabled=color_enabled)
    started_at = perf_counter()
    event = DaprPubSubSmokeEvent(
        operation_id=operation_id,
        correlation_id=correlation_id,
        message=message,
    )

    output.write(f"{palette.heading('Dapr pub/sub smoke')}\n")
    output.write(f"Correlation: {event.correlation_id}\n")
    output.write(f"Operation: {event.operation_id}\n")
    output.write(f"Component: {DAPR_PUBSUB_SMOKE_PUBSUB_NAME}\n")
    output.write(f"Topic: {DAPR_PUBSUB_SMOKE_TOPIC}\n")
    output.write("Checks: 2\n")
    output.write("Mode: API publishes through Dapr, worker consumes through Dapr.\n")
    output.write("Requires local Dapr sidecars, API service, and Worker service.\n\n")
    output.flush()

    owns_client = http_client is None
    client = http_client or httpx.AsyncClient(timeout=timeout_seconds)
    try:
        results = await _run_checks(
            client=client,
            api_base_url=api_base_url,
            worker_base_url=worker_base_url,
            event=event,
            timeout_seconds=timeout_seconds,
            progress_interval_seconds=progress_interval_seconds,
            palette=palette,
            output=output,
        )
    finally:
        if owns_client:
            await client.aclose()

    _print_summary(
        results,
        elapsed_seconds=perf_counter() - started_at,
        palette=palette,
        output=output,
    )
    return 0 if all(result.passed for result in results) else 1


async def _run_checks(
    *,
    client: httpx.AsyncClient,
    api_base_url: str,
    worker_base_url: str,
    event: DaprPubSubSmokeEvent,
    timeout_seconds: float,
    progress_interval_seconds: float,
    palette: _Palette,
    output: TextIO,
) -> tuple[DaprPubSubSmokeStepResult, DaprPubSubSmokeStepResult]:
    publish_result = await _run_with_progress(
        "[01/02] Publishing smoke event through API",
        lambda: publish_dapr_pubsub_smoke_event(
            client=client,
            api_base_url=api_base_url,
            event=event,
        ),
        progress_interval_seconds=progress_interval_seconds,
        palette=palette,
        output=output,
    )
    consume_result = await _run_with_progress(
        "[02/02] Waiting for worker consumption",
        lambda: wait_for_dapr_pubsub_smoke_consumption(
            client=client,
            worker_base_url=worker_base_url,
            event=event,
            timeout_seconds=timeout_seconds,
            poll_interval_seconds=progress_interval_seconds,
        ),
        progress_interval_seconds=progress_interval_seconds,
        palette=palette,
        output=output,
    )

    return (publish_result, consume_result)


async def _run_with_progress(
    label: str,
    operation: _StepOperation,
    *,
    progress_interval_seconds: float,
    palette: _Palette,
    output: TextIO,
) -> DaprPubSubSmokeStepResult:
    output.write(f"{label} ")
    output.flush()

    task = asyncio.create_task(operation())
    printed_dot = False
    while not task.done():
        output.write(".")
        output.flush()
        printed_dot = True
        await asyncio.sleep(progress_interval_seconds)

    if not printed_dot:
        output.write(".")
        output.flush()

    try:
        result = await task
    except Exception as error:  # pragma: no cover - defensive CLI boundary
        result = DaprPubSubSmokeStepResult(
            name="unexpected",
            url="<unavailable>",
            status_code=None,
            operation_id="<unknown>",
            detail="unexpected-error",
            failure=f"unexpected smoke runner error: {type(error).__name__}: {error}",
        )

    status = palette.ok("OK") if result.passed else palette.fail("FAIL")
    output.write(f" {status} {_format_result_detail(result)}\n")
    output.flush()

    return result


type _StepOperation = Callable[[], Coroutine[Any, Any, DaprPubSubSmokeStepResult]]


def _print_summary(
    results: tuple[DaprPubSubSmokeStepResult, ...],
    *,
    elapsed_seconds: float,
    palette: _Palette,
    output: TextIO,
) -> None:
    failures = tuple(result for result in results if not result.passed)
    passed_count = len(results) - len(failures)

    output.write("\n")
    output.write(f"{palette.heading('Summary')}\n")
    output.write(f"Passed: {passed_count}/{len(results)}\n")
    output.write(f"Failed: {len(failures)}\n")
    output.write(f"Duration: {elapsed_seconds:.2f}s\n")

    if failures:
        output.write(f"\n{palette.fail('Dapr pub/sub smoke failed.')}\n")
        output.flush()
        return

    output.write(f"\n{palette.ok('Dapr pub/sub smoke passed.')}\n")
    output.flush()


def _format_result_detail(result: DaprPubSubSmokeStepResult) -> str:
    status = "transport-error" if result.status_code is None else str(result.status_code)
    detail = f"url={result.url} status={status} operation={result.operation_id} {result.detail}"
    if result.failure is not None:
        detail = f"{detail} reason={_single_line(result.failure)}"

    return detail


def _single_line(value: str) -> str:
    return " ".join(value.split())


def _parse_args(argv: Sequence[str] | None) -> _CliArgs:
    parser = argparse.ArgumentParser(
        description=(
            "Run the local DocMind Dapr pub/sub smoke check. "
            "API, Worker, and local Dapr sidecars must already be running."
        ),
    )
    parser.add_argument(
        "--api-base-url",
        default=environ.get(_API_BASE_URL_ENV, DEFAULT_PUBSUB_SMOKE_API_BASE_URL),
        help=(
            "API service base URL "
            f"(default: ${_API_BASE_URL_ENV} or {DEFAULT_PUBSUB_SMOKE_API_BASE_URL})."
        ),
    )
    parser.add_argument(
        "--worker-base-url",
        default=environ.get(_WORKER_BASE_URL_ENV, DEFAULT_PUBSUB_SMOKE_WORKER_BASE_URL),
        help=(
            "Worker service base URL "
            f"(default: ${_WORKER_BASE_URL_ENV} or {DEFAULT_PUBSUB_SMOKE_WORKER_BASE_URL})."
        ),
    )
    parser.add_argument(
        "--operation-id",
        default=new_dapr_pubsub_smoke_operation_id(),
        help="Operation id used to correlate the published and consumed smoke event.",
    )
    parser.add_argument(
        "--correlation-id",
        default=environ.get(_CORRELATION_ID_ENV, DEFAULT_PUBSUB_SMOKE_CORRELATION_ID),
        help=(
            "Correlation id sent through the smoke flow "
            f"(default: ${_CORRELATION_ID_ENV} or {DEFAULT_PUBSUB_SMOKE_CORRELATION_ID})."
        ),
    )
    parser.add_argument(
        "--message",
        default=DEFAULT_PUBSUB_SMOKE_MESSAGE,
        help="Message field included in the technical smoke event.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=_DEFAULT_TIMEOUT_SECONDS,
        help="Seconds to wait for worker consumption.",
    )
    parser.add_argument(
        "--progress-interval",
        type=float,
        default=_DEFAULT_PROGRESS_INTERVAL_SECONDS,
        help="Seconds between progress dots while a check is running.",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable ANSI colors in terminal output.",
    )

    namespace = parser.parse_args(argv)
    return _CliArgs(
        api_base_url=str(namespace.api_base_url),
        worker_base_url=str(namespace.worker_base_url),
        operation_id=str(namespace.operation_id),
        correlation_id=str(namespace.correlation_id),
        message=str(namespace.message),
        timeout_seconds=max(float(namespace.timeout), 0.1),
        progress_interval_seconds=max(float(namespace.progress_interval), 0.05),
        no_color=bool(namespace.no_color),
    )


if __name__ == "__main__":
    raise SystemExit(main())
