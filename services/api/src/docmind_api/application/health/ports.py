"""Application ports for API service health checks."""

from typing import Protocol

from docmind_api.domain.health.models import HealthCheckResult


class HealthProbe(Protocol):
    """Port implemented by infrastructure health probes."""

    @property
    def name(self) -> str: ...

    @property
    def critical(self) -> bool: ...

    async def check(self) -> HealthCheckResult: ...
