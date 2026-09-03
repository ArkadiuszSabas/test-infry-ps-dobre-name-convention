"""Safe OpenTelemetry metrics for durable OCR admission."""

from __future__ import annotations

from dataclasses import dataclass
from threading import Lock

from opentelemetry import metrics
from opentelemetry.metrics import Observation


@dataclass(frozen=True, slots=True)
class OcrAdmissionSnapshot:
    waiting_runs: int
    oldest_waiting_age_seconds: float
    reserved_leases: int
    running_leases: int


class _OcrAdmissionMetrics:
    def __init__(self) -> None:
        self._lock = Lock()
        self._snapshot = OcrAdmissionSnapshot(0, 0.0, 0, 0)
        meter = metrics.get_meter("docmind.api.ocr_admission")
        self._deferrals = meter.create_counter("docmind.api.ocr_admission.deferrals")
        self._reservation_expirations = meter.create_counter(
            "docmind.api.ocr_admission.reservation_expirations"
        )
        self._waiting_runs = meter.create_observable_gauge(
            "docmind.api.ocr_admission.waiting_runs",
            callbacks=[self._observe_waiting_runs],
        )
        self._oldest_waiting_age = meter.create_observable_gauge(
            "docmind.api.ocr_admission.oldest_waiting_age_seconds",
            callbacks=[self._observe_oldest_waiting_age],
        )
        self._active_leases = meter.create_observable_gauge(
            "docmind.api.ocr_admission.active_leases",
            callbacks=[self._observe_active_leases],
        )

    def record_deferral(self) -> None:
        self._deferrals.add(1)

    def record_reservation_expiration(self) -> None:
        self._reservation_expirations.add(1)

    def update_snapshot(self, snapshot: OcrAdmissionSnapshot) -> None:
        with self._lock:
            self._snapshot = snapshot

    def _current(self) -> OcrAdmissionSnapshot:
        with self._lock:
            return self._snapshot

    def _observe_waiting_runs(self, _options: object) -> list[Observation]:
        return [Observation(self._current().waiting_runs)]

    def _observe_oldest_waiting_age(self, _options: object) -> list[Observation]:
        return [Observation(self._current().oldest_waiting_age_seconds)]

    def _observe_active_leases(self, _options: object) -> list[Observation]:
        snapshot = self._current()
        return [
            Observation(snapshot.reserved_leases, {"status": "reserved"}),
            Observation(snapshot.running_leases, {"status": "running"}),
        ]


_METRICS = _OcrAdmissionMetrics()


def record_ocr_admission_deferral() -> None:
    _METRICS.record_deferral()


def record_ocr_reservation_expiration() -> None:
    _METRICS.record_reservation_expiration()


def update_ocr_admission_snapshot(snapshot: OcrAdmissionSnapshot) -> None:
    _METRICS.update_snapshot(snapshot)
