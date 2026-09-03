"""Dapr service-invocation adapters for Worker OCR run dispatch."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import datetime

from pydantic import BaseModel, ConfigDict, ValidationError

from docmind_backend_runtime import (
    DaprClientError,
    DaprClientTimeoutError,
    DaprHttpClient,
    get_correlation_id,
)
from docmind_backend_runtime.correlation import CORRELATION_ID_HEADER
from docmind_core.ocr_pipeline import (
    DispatchFailedV1,
    OcrDispatchDispositionV1,
    OcrDispatchFailureCodeV1,
)
from docmind_worker.application.ocr_pipeline_runs.ports import (
    OcrRunCancellationRequest,
    OcrRunDispatchAdmission,
)
from docmind_worker.application.ocr_pipeline_runs.service import OcrRunDispatchRetryableError

_API_APP_ID = "docmind-api"
_LLMMAGIC_APP_ID = "docmind-llmmagic"
_DISPATCH_METHOD_PREFIX = "internal/ocr/pipeline-runs"
_LLMMAGIC_RUN_METHOD = "internal/ocr/pipeline-runs"


class _DispatchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    disposition: OcrDispatchDispositionV1
    attempt_id: str | None = None
    attempt_number: int | None = None
    fencing_token: int | None = None
    execution_deadline_at: datetime | None = None
    run_request: dict[str, object] | None = None


class DaprOcrRunDispatchGateway:
    """Calls API and LLM Magic through the Worker's Dapr sidecar."""

    def __init__(self, *, dapr_client_factory: Callable[[], DaprHttpClient]) -> None:
        self._dapr_client_factory = dapr_client_factory

    async def dispatch(self, run_id: str) -> OcrRunDispatchAdmission:
        try:
            response = await self._dapr_client_factory().invoke_method(
                _API_APP_ID,
                f"{_DISPATCH_METHOD_PREFIX}/{run_id}/dispatch",
                http_method="POST",
                headers=_correlation_headers(),
            )
        except (DaprClientError, DaprClientTimeoutError) as error:
            raise OcrRunDispatchRetryableError("API dispatch invocation failed.") from error
        if response.status_code in {408, 429} or response.status_code >= 500:
            raise OcrRunDispatchRetryableError("API dispatch is temporarily unavailable.")
        if not 200 <= response.status_code < 300:
            raise OcrRunDispatchRetryableError("API dispatch returned an unexpected status.")
        try:
            payload = _DispatchResponse.model_validate(response.json())
        except (UnicodeDecodeError, ValueError, ValidationError) as error:
            raise OcrRunDispatchRetryableError("API dispatch response is invalid.") from error
        return OcrRunDispatchAdmission(
            disposition=payload.disposition.value,
            attempt_id=payload.attempt_id,
            fencing_token=payload.fencing_token,
            run_request=payload.run_request,
        )

    async def invoke(self, run_request: Mapping[str, object]) -> int:
        try:
            response = await self._dapr_client_factory().invoke_method(
                _LLMMAGIC_APP_ID,
                _LLMMAGIC_RUN_METHOD,
                http_method="POST",
                headers=_correlation_headers(),
                json_body=run_request,
            )
        except (DaprClientError, DaprClientTimeoutError) as error:
            raise OcrRunDispatchRetryableError("LLM Magic dispatch invocation failed.") from error
        return response.status_code

    async def dispatch_failed(self, *, run_id: str, attempt_id: str, fencing_token: int) -> int:
        try:
            response = await self._dapr_client_factory().invoke_method(
                _API_APP_ID,
                f"{_DISPATCH_METHOD_PREFIX}/{run_id}/attempts/{attempt_id}/dispatch-failed",
                http_method="POST",
                headers=_correlation_headers(),
                json_body=DispatchFailedV1(
                    fencing_token=fencing_token,
                    code=OcrDispatchFailureCodeV1.LLMMAGIC_DISPATCH_REJECTED,
                ).model_dump(mode="json"),
            )
        except (DaprClientError, DaprClientTimeoutError) as error:
            raise OcrRunDispatchRetryableError("API dispatch failure invocation failed.") from error
        if response.status_code in {408, 429} or response.status_code >= 500:
            raise OcrRunDispatchRetryableError("API dispatch failure is temporarily unavailable.")
        return response.status_code

    async def dispatch_deferred(self, *, run_id: str, attempt_id: str, fencing_token: int) -> int:
        try:
            response = await self._dapr_client_factory().invoke_method(
                _API_APP_ID,
                f"{_DISPATCH_METHOD_PREFIX}/{run_id}/attempts/{attempt_id}/dispatch-deferred",
                http_method="POST",
                headers=_correlation_headers(),
                json_body={"fencing_token": fencing_token},
            )
        except (DaprClientError, DaprClientTimeoutError) as error:
            raise OcrRunDispatchRetryableError(
                "API dispatch deferral invocation failed."
            ) from error
        if response.status_code in {408, 429} or response.status_code >= 500:
            raise OcrRunDispatchRetryableError("API dispatch deferral is temporarily unavailable.")
        return response.status_code

    async def cancel(self, request: OcrRunCancellationRequest) -> int:
        try:
            response = await self._dapr_client_factory().invoke_method(
                _LLMMAGIC_APP_ID,
                (
                    f"{_DISPATCH_METHOD_PREFIX}/{request.run_id}/attempts/"
                    f"{request.attempt_id}/cancel"
                ),
                http_method="POST",
                headers=_correlation_headers(request.correlation_id),
                json_body={
                    "fencing_token": request.fencing_token,
                    "document_id": request.document_id,
                    "pipeline_id": request.pipeline_id,
                    "next_event_sequence": request.next_event_sequence,
                    "correlation_id": request.correlation_id,
                },
            )
        except (DaprClientError, DaprClientTimeoutError) as error:
            raise OcrRunDispatchRetryableError(
                "LLM Magic cancellation invocation failed."
            ) from error
        return response.status_code

    async def cancel_dispatch_failed(self, request: OcrRunCancellationRequest) -> int:
        try:
            response = await self._dapr_client_factory().invoke_method(
                _API_APP_ID,
                (
                    f"{_DISPATCH_METHOD_PREFIX}/{request.run_id}/attempts/"
                    f"{request.attempt_id}/cancel-dispatch-failed"
                ),
                http_method="POST",
                headers=_correlation_headers(request.correlation_id),
                json_body={
                    "fencing_token": request.fencing_token,
                    "code": "OCR_PIPELINE_RUN_CANCELLATION_REJECTED",
                },
            )
        except (DaprClientError, DaprClientTimeoutError) as error:
            raise OcrRunDispatchRetryableError(
                "API cancellation failure invocation failed."
            ) from error
        if response.status_code in {408, 429} or response.status_code >= 500:
            raise OcrRunDispatchRetryableError(
                "API cancellation failure boundary is temporarily unavailable."
            )
        return response.status_code


def _correlation_headers(explicit_correlation_id: str | None = None) -> Mapping[str, str]:
    correlation_id = explicit_correlation_id or get_correlation_id()
    return {} if correlation_id is None else {CORRELATION_ID_HEADER: correlation_id}
