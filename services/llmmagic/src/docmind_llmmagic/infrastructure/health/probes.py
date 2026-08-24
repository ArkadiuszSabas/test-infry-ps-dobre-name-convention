"""Infrastructure health probe implementations."""

from docmind_llmmagic.domain.health.models import HealthCheckResult, HealthStatus


class RuntimeHealthProbe:
    """Probe that confirms the FastAPI process can execute application code."""

    def __init__(self, *, name: str = "llmmagic-runtime", critical: bool = True) -> None:
        self._name = name
        self._critical = critical

    @property
    def name(self) -> str:
        """Return the stable probe name."""

        return self._name

    @property
    def critical(self) -> bool:
        """Return whether this probe affects aggregate readiness."""

        return self._critical

    async def check(self) -> HealthCheckResult:
        """Return healthy when the process can execute this probe."""

        return HealthCheckResult(
            name=self.name,
            status=HealthStatus.HEALTHY,
            critical=self.critical,
        )
