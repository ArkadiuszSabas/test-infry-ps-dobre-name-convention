"""Health use cases for the API service."""

import logging
from collections.abc import Sequence

from docmind_api.application.health.ports import HealthProbe
from docmind_api.domain.health.models import HealthCheckResult, HealthReport, HealthStatus
from docmind_api.domain.health.policies import aggregate_health_status

_LOGGER = logging.getLogger(__name__)


class HealthService:
    """Application service that builds liveness and readiness reports."""

    def __init__(
        self,
        *,
        liveness_probes: Sequence[HealthProbe],
        readiness_probes: Sequence[HealthProbe],
    ) -> None:
        self._liveness_probes = tuple(liveness_probes)
        self._readiness_probes = tuple(readiness_probes)

    async def get_liveness(self) -> HealthReport:
        """Return process-level liveness without checking external dependencies."""

        return await self._build_report(name="liveness", probes=self._liveness_probes)

    async def get_readiness(self) -> HealthReport:
        """Return readiness for accepting traffic."""

        return await self._build_report(name="readiness", probes=self._readiness_probes)

    async def _build_report(
        self,
        *,
        name: str,
        probes: Sequence[HealthProbe],
    ) -> HealthReport:
        checks = await self._collect_checks(probes)
        return HealthReport(
            name=name,
            status=aggregate_health_status(checks),
            checks=checks,
        )

    @staticmethod
    async def _collect_checks(probes: Sequence[HealthProbe]) -> tuple[HealthCheckResult, ...]:
        checks: list[HealthCheckResult] = []

        for probe in probes:
            try:
                checks.append(await probe.check())
            except Exception:
                _LOGGER.exception(
                    "Health probe failed.",
                    extra={"probe_name": probe.name, "probe_critical": probe.critical},
                )
                checks.append(
                    HealthCheckResult(
                        name=probe.name,
                        status=HealthStatus.UNHEALTHY,
                        critical=probe.critical,
                        reason="probe_failed",
                    ),
                )

        return tuple(checks)
