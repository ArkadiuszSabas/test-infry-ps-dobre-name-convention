"""Health aggregation policies."""

from collections.abc import Sequence

from docmind_llmmagic.domain.health.models import HealthCheckResult, HealthStatus


def aggregate_health_status(checks: Sequence[HealthCheckResult]) -> HealthStatus:
    """Return unhealthy when any critical check is unhealthy."""

    has_unhealthy_critical_check = any(
        check.critical and check.status == HealthStatus.UNHEALTHY for check in checks
    )
    if has_unhealthy_critical_check:
        return HealthStatus.UNHEALTHY

    return HealthStatus.HEALTHY
