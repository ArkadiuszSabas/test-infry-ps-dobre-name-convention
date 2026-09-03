"""Idempotent Worker orchestration for one OCR run delivery."""

import logging

from docmind_worker.application.ocr_pipeline_runs.ports import (
    NoopOcrRunDispatchMetrics,
    OcrRunCancellationApi,
    OcrRunCancellationRequest,
    OcrRunDispatchApi,
    OcrRunDispatchMetrics,
    OcrRunDispatchRequest,
    OcrRunPipelineInvoker,
)

_LOGGER = logging.getLogger(__name__)


class OcrRunDispatchRetryableError(RuntimeError):
    """Signals that Dapr must redeliver the original OCR run event."""


class OcrRunDispatchConsumer:
    """Admits and forwards a whole OCR run without owning workflow state."""

    def __init__(
        self,
        *,
        api: OcrRunDispatchApi,
        pipeline_invoker: OcrRunPipelineInvoker,
        metrics: OcrRunDispatchMetrics | None = None,
    ) -> None:
        self._api = api
        self._pipeline_invoker = pipeline_invoker
        self._metrics = metrics or NoopOcrRunDispatchMetrics()

    async def consume(self, event: OcrRunDispatchRequest) -> None:
        """Process one delivery, leaving retries and DLQ ownership to Dapr."""

        try:
            admission = await self._api.dispatch(event.run_id)
            if admission.disposition != "dispatchable":
                self._metrics.record(f"noop_{admission.disposition}")
                _LOGGER.info(
                    "OCR run dispatch is an idempotent no-op.",
                    extra={
                        "ocr_run_id": event.run_id,
                        "ocr_dispatch_disposition": admission.disposition,
                    },
                )
                return

            if (
                admission.attempt_id is None
                or admission.fencing_token is None
                or admission.run_request is None
            ):
                raise OcrRunDispatchRetryableError("API returned an incomplete dispatch admission.")

            status_code = await self._pipeline_invoker.invoke(admission.run_request)
            if status_code == 202:
                self._metrics.record("accepted")
                _LOGGER.info(
                    "OCR run was accepted by LLM Magic.",
                    extra={"ocr_run_id": event.run_id, "ocr_dispatch_status": status_code},
                )
                return
            if status_code == 429:
                self._metrics.record("local_capacity_rejected")
                deferred_status = await self._api.dispatch_deferred(
                    run_id=event.run_id,
                    attempt_id=admission.attempt_id,
                    fencing_token=admission.fencing_token,
                )
                if deferred_status != 204:
                    raise OcrRunDispatchRetryableError(
                        "API dispatch deferral recording should be retried."
                    )
                self._metrics.record("deferred")
                return
            if status_code == 408 or status_code >= 500:
                raise OcrRunDispatchRetryableError("LLM Magic dispatch should be retried.")
            if 400 <= status_code < 500:
                failure_status = await self._api.dispatch_failed(
                    run_id=event.run_id,
                    attempt_id=admission.attempt_id,
                    fencing_token=admission.fencing_token,
                )
                if failure_status != 204:
                    raise OcrRunDispatchRetryableError(
                        "API dispatch failure recording should be retried."
                    )
                _LOGGER.warning(
                    "LLM Magic permanently rejected an OCR run dispatch.",
                    extra={
                        "ocr_run_id": event.run_id,
                        "ocr_dispatch_status": status_code,
                        "ocr_dispatch_code": "LLMMAGIC_DISPATCH_REJECTED",
                    },
                )
                self._metrics.record("permanent_reject")
                return

            raise OcrRunDispatchRetryableError("LLM Magic returned an unexpected dispatch status.")
        except OcrRunDispatchRetryableError:
            self._metrics.record("retry")
            raise


class OcrRunCancellationConsumer:
    """Forward one fenced cancellation command and acknowledge only durable outcomes."""

    def __init__(
        self,
        *,
        api: OcrRunCancellationApi,
        pipeline_invoker: OcrRunPipelineInvoker,
    ) -> None:
        self._api = api
        self._pipeline_invoker = pipeline_invoker

    async def consume(self, request: OcrRunCancellationRequest) -> None:
        status_code = await self._pipeline_invoker.cancel(request)
        if status_code == 202:
            return
        if status_code in {408, 429} or status_code >= 500:
            raise OcrRunDispatchRetryableError("LLM Magic cancellation should be retried.")
        if 400 <= status_code < 500:
            failure_status = await self._api.cancel_dispatch_failed(request)
            if failure_status != 204:
                raise OcrRunDispatchRetryableError(
                    "API cancellation failure recording should be retried."
                )
            return
        raise OcrRunDispatchRetryableError("LLM Magic returned an unexpected cancel status.")
