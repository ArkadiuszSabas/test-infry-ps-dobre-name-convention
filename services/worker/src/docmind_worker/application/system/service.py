"""Application service for worker service discovery metadata."""

from docmind_worker.domain.system.models import ServiceInfo


class ServiceInfoService:
    """Return stable technical metadata about the worker service."""

    def __init__(self, *, service_name: str) -> None:
        self._service_name = service_name

    async def get_service_info(self) -> ServiceInfo:
        """Return static service discovery metadata."""
        return ServiceInfo(
            service_name=self._service_name,
            title="DocMind.ai Worker",
        )
