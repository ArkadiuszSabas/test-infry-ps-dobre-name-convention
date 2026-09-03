"""Application ports for Worker OCR run dispatch."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal, Protocol

OcrRunDispatchDisposition = Literal["dispatchable", "deferred", "active", "terminal", "deleted"]


@dataclass(frozen=True, slots=True)
class OcrRunDispatchRequest:
    """Framework-free identity for one validated OCR run delivery."""

    run_id: str


@dataclass(frozen=True, slots=True)
class OcrRunDispatchAdmission:
    """API-owned admission result for one OCR run event."""

    disposition: OcrRunDispatchDisposition
    attempt_id: str | None = None
    fencing_token: int | None = None
    run_request: Mapping[str, object] | None = None


@dataclass(frozen=True, slots=True)
class OcrRunCancellationRequest:
    run_id: str
    document_id: str
    pipeline_id: str
    attempt_id: str
    fencing_token: int
    next_event_sequence: int
    correlation_id: str


class OcrRunDispatchApi(Protocol):
    """Calls the API-owned OCR run admission and failure boundaries."""

    async def dispatch(self, run_id: str) -> OcrRunDispatchAdmission: ...

    async def dispatch_failed(self, *, run_id: str, attempt_id: str, fencing_token: int) -> int: ...

    async def dispatch_deferred(
        self,
        *,
        run_id: str,
        attempt_id: str,
        fencing_token: int,
    ) -> int: ...


class OcrRunPipelineInvoker(Protocol):
    """Forwards an already-admitted opaque pipeline request to LLM Magic."""

    async def invoke(self, run_request: Mapping[str, object]) -> int: ...

    async def cancel(self, request: OcrRunCancellationRequest) -> int: ...


class OcrRunCancellationApi(Protocol):
    async def cancel_dispatch_failed(self, request: OcrRunCancellationRequest) -> int: ...


class OcrRunDispatchMetrics(Protocol):
    """Records a safe outcome for one OCR dispatch delivery."""

    def record(self, outcome: str) -> None: ...


class NoopOcrRunDispatchMetrics:
    """Default metrics sink used by focused application tests."""

    def record(self, outcome: str) -> None:
        return None
