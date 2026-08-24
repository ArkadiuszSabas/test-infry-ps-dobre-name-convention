"""Health dependency factories for the DocMind.ai API service."""

from docmind_api.application.health.service import HealthService
from docmind_api.infrastructure.health.probes import RuntimeHealthProbe


def get_health_service() -> HealthService:
    """Build the health application service for one request."""
    runtime_probe = RuntimeHealthProbe()
    return HealthService(
        liveness_probes=(runtime_probe,),
        readiness_probes=(runtime_probe,),
    )
