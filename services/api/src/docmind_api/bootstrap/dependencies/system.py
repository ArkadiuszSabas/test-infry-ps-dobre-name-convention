"""System dependency factories for the DocMind.ai API service."""

from collections.abc import Callable

from docmind_api.application.system.service import ServiceInfoService
from docmind_backend_runtime import RuntimeSettings


def build_service_info_service_dependency(
    settings: RuntimeSettings,
) -> Callable[[], ServiceInfoService]:
    """Build a request dependency for service discovery metadata."""

    def get_service_info_service() -> ServiceInfoService:
        return ServiceInfoService(service_name=settings.service_name)

    return get_service_info_service
