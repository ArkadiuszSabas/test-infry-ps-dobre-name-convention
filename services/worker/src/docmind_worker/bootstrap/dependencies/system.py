"""System dependency factories for the DocMind.ai worker service."""

from collections.abc import Callable

from docmind_backend_runtime import RuntimeSettings
from docmind_worker.application.system.service import ServiceInfoService


def build_service_info_service_dependency(
    settings: RuntimeSettings,
) -> Callable[[], ServiceInfoService]:
    """Build a request dependency for service discovery metadata."""

    def get_service_info_service() -> ServiceInfoService:
        return ServiceInfoService(service_name=settings.service_name)

    return get_service_info_service
