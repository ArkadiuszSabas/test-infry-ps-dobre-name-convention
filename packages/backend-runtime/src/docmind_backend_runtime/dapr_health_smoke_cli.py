"""Terminal CLI for the local Dapr health smoke check."""

from __future__ import annotations

import argparse
import asyncio
from collections.abc import Sequence
from dataclasses import dataclass
from os import environ
from sys import stdout
from time import perf_counter
from typing import TextIO

from docmind_backend_runtime.dapr import create_dapr_client
from docmind_backend_runtime.dapr_health_smoke import (
    DEFAULT_CORRELATION_ID,
    DaprClientFactory,
    DaprHealthSmokeInvocation,
    DaprHealthSmokeReport,
    DaprHealthSmokeResult,
    build_dapr_health_smoke_matrix,
    check_dapr_health_invocation,
    docmind_local_dapr_health_smoke_sources,
)

_CORRELATION_ID_ENV = "DOCMIND_DAPR_HEALTH_SMOKE_CORRELATION_ID"
_DEFAULT_PROGRESS_INTERVAL_SECONDS = 0.25


@dataclass(frozen=True, slots=True)
class _CliArgs:
    correlation_id: str
    no_color: bool
    progress_interval_seconds: float


@dataclass(frozen=True, slots=True)
class _Palette:
    enabled: bool

    def heading(self, value: str) -> str:
        return self._style(value, "1")

    def ok(self, value: str) -> str:
        return self._style(value, "32")

    def fail(self, value: str) -> str:
        return self._style(value, "31")

    def muted(self, value: str) -> str:
        return self._style(value, "90")

    def _style(self, value: str, code: str) -> str:
        if not self.enabled:
            return value

        return f"\033[{code}m{value}\033[0m"


def main(argv: Sequence[str] | None = None) -> int:
    """Run the Dapr health smoke CLI."""

    args = _parse_args(argv)
    try:
        return asyncio.run(
            run_local_dapr_health_smoke_cli(
                correlation_id=args.correlation_id,
                progress_interval_seconds=args.progress_interval_seconds,
                color_enabled=not args.no_color and "NO_COLOR" not in environ,
                output=stdout,
            ),
        )
    except KeyboardInterrupt:
        stdout.write("\nDapr health smoke interrupted.\n")
        return 130


async def run_local_dapr_health_smoke_cli(
    *,
    correlation_id: str,
    progress_interval_seconds: float = _DEFAULT_PROGRESS_INTERVAL_SECONDS,
    color_enabled: bool = True,
    output: TextIO = stdout,
    client_factory: DaprClientFactory = create_dapr_client,
) -> int:
    """Run the local DocMind Dapr health smoke with human-oriented progress output."""

    invocations = build_dapr_health_smoke_matrix(docmind_local_dapr_health_smoke_sources())
    palette = _Palette(enabled=color_enabled)
    started_at = perf_counter()

    output.write(f"{palette.heading('Dapr health smoke')}\n")
    output.write(f"Correlation: {correlation_id}\n")
    output.write(f"Checks: {len(invocations)}\n")
    output.write("Mode: source sidecar -> target service /health/ready\n")
    output.write("Requires local Dapr sidecars and target FastAPI services.\n\n")
    output.flush()

    results: list[DaprHealthSmokeResult] = []
    for index, invocation in enumerate(invocations, start=1):
        result = await _run_with_progress(
            invocation,
            index=index,
            total=len(invocations),
            correlation_id=correlation_id,
            progress_interval_seconds=progress_interval_seconds,
            palette=palette,
            output=output,
            client_factory=client_factory,
        )
        results.append(result)

    report = DaprHealthSmokeReport(results=tuple(results))
    _print_summary(
        report,
        elapsed_seconds=perf_counter() - started_at,
        palette=palette,
        output=output,
    )

    return 0 if report.passed else 1


async def _run_with_progress(
    invocation: DaprHealthSmokeInvocation,
    *,
    index: int,
    total: int,
    correlation_id: str,
    progress_interval_seconds: float,
    palette: _Palette,
    output: TextIO,
    client_factory: DaprClientFactory,
) -> DaprHealthSmokeResult:
    label = (
        f"[{index:02d}/{total:02d}] Testing "
        f"{invocation.source.name} sidecar -> {invocation.target.name} {invocation.path}"
    )
    output.write(f"{label} ")
    output.flush()

    task = asyncio.create_task(
        check_dapr_health_invocation(
            invocation,
            correlation_id=correlation_id,
            client_factory=client_factory,
        ),
    )
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
        result = _unexpected_error_result(invocation, error)

    status = palette.ok("OK") if result.passed else palette.fail("FAIL")
    output.write(f" {status} {_format_result_detail(result)}\n")
    output.flush()

    return result


def _print_summary(
    report: DaprHealthSmokeReport,
    *,
    elapsed_seconds: float,
    palette: _Palette,
    output: TextIO,
) -> None:
    passed_count = len(report.results) - len(report.failures)
    output.write("\n")
    output.write(f"{palette.heading('Summary')}\n")
    output.write(f"Passed: {passed_count}/{len(report.results)}\n")
    output.write(f"Failed: {len(report.failures)}\n")
    output.write(f"Duration: {elapsed_seconds:.2f}s\n")

    if report.passed:
        output.write(f"\n{palette.ok('Dapr health smoke passed.')}\n")
        output.flush()
        return

    output.write(f"\n{palette.fail('Dapr health smoke failed.')}\n")
    output.flush()


def _format_result_detail(result: DaprHealthSmokeResult) -> str:
    status = "transport-error" if result.status_code is None else str(result.status_code)
    detail = (
        f"url={result.invocation_url or '<unavailable>'} "
        f"status={status} "
        f"health={result.health_status or '<missing>'} "
        f"correlation={result.response_correlation_id or '<missing>'}"
    )
    if result.failure is not None:
        detail = f"{detail} reason={_single_line(result.failure)}"

    return detail


def _single_line(value: str) -> str:
    return " ".join(value.split())


def _unexpected_error_result(
    invocation: DaprHealthSmokeInvocation,
    error: Exception,
) -> DaprHealthSmokeResult:
    return DaprHealthSmokeResult(
        source_name=invocation.source.name,
        source_app_id=invocation.source.app_id,
        target_name=invocation.target.name,
        target_app_id=invocation.target.app_id,
        path=invocation.path,
        status_code=None,
        response_correlation_id=None,
        health_status=None,
        failure=f"unexpected smoke runner error: {type(error).__name__}: {error}",
    )


def _parse_args(argv: Sequence[str] | None) -> _CliArgs:
    parser = argparse.ArgumentParser(
        description=(
            "Run the local DocMind Dapr service invocation health smoke check. "
            "FastAPI services and Dapr sidecars must already be running."
        ),
    )
    parser.add_argument(
        "--correlation-id",
        default=environ.get(_CORRELATION_ID_ENV, DEFAULT_CORRELATION_ID),
        help=(
            "Correlation id sent through every Dapr invocation "
            f"(default: ${_CORRELATION_ID_ENV} or {DEFAULT_CORRELATION_ID})."
        ),
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
    progress_interval = max(float(namespace.progress_interval), 0.05)

    return _CliArgs(
        correlation_id=str(namespace.correlation_id),
        no_color=bool(namespace.no_color),
        progress_interval_seconds=progress_interval,
    )


if __name__ == "__main__":
    raise SystemExit(main())
