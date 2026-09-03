"""OpenTelemetry metrics for safe Worker OCR dispatch outcomes."""

from opentelemetry import metrics


class OpenTelemetryOcrRunDispatchMetrics:
    """Emits one bounded counter without document or payload attributes."""

    def __init__(self) -> None:
        meter = metrics.get_meter("docmind.worker.ocr_dispatch")
        self._counter = meter.create_counter("docmind.worker.ocr_dispatch.deliveries")

    def record(self, outcome: str) -> None:
        self._counter.add(1, {"outcome": outcome})
