"""Dependency factories for Worker OCR run dispatch."""

from collections.abc import Callable

from docmind_backend_runtime import DaprHttpClient, create_dapr_client
from docmind_worker.application.ocr_pipeline_runs.service import (
    OcrRunCancellationConsumer,
    OcrRunDispatchConsumer,
)
from docmind_worker.infrastructure.ocr_pipeline_runs.dapr_dispatch import DaprOcrRunDispatchGateway
from docmind_worker.infrastructure.ocr_pipeline_runs.metrics import (
    OpenTelemetryOcrRunDispatchMetrics,
)
from docmind_worker.settings import get_dapr_client_settings


def build_ocr_run_dispatch_consumer_dependency() -> Callable[[], OcrRunDispatchConsumer]:
    """Build the stateless OCR dispatch consumer."""

    gateway = DaprOcrRunDispatchGateway(dapr_client_factory=_create_dapr_client)
    consumer = OcrRunDispatchConsumer(
        api=gateway,
        pipeline_invoker=gateway,
        metrics=OpenTelemetryOcrRunDispatchMetrics(),
    )

    def get_ocr_run_dispatch_consumer() -> OcrRunDispatchConsumer:
        return consumer

    return get_ocr_run_dispatch_consumer


def build_ocr_run_cancellation_consumer_dependency() -> Callable[[], OcrRunCancellationConsumer]:
    gateway = DaprOcrRunDispatchGateway(dapr_client_factory=_create_dapr_client)
    consumer = OcrRunCancellationConsumer(api=gateway, pipeline_invoker=gateway)

    def get_ocr_run_cancellation_consumer() -> OcrRunCancellationConsumer:
        return consumer

    return get_ocr_run_cancellation_consumer


def _create_dapr_client() -> DaprHttpClient:
    return create_dapr_client(get_dapr_client_settings())
