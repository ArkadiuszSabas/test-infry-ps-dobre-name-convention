"""Framework-free health domain models."""

from dataclasses import dataclass
from enum import StrEnum


class HealthStatus(StrEnum):
    """Health status returned by service probes."""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"


@dataclass(frozen=True, slots=True)
class HealthCheckResult:
    """Result of one health probe."""

    name: str
    status: HealthStatus
    critical: bool = True
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class HealthReport:
    """Aggregated service health report."""

    name: str
    status: HealthStatus
    checks: tuple[HealthCheckResult, ...]
