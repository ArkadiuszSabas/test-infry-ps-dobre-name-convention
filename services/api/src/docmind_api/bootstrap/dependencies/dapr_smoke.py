"""Dependency factories for the API-owned Dapr smoke slice."""

from docmind_api.application.dapr_smoke.service import PublishDaprSmokeEventUseCase
from docmind_api.infrastructure.dapr_smoke.publisher import DaprHttpSmokeEventPublisher
from docmind_api.settings import get_dapr_client_settings
from docmind_backend_runtime import create_dapr_client


def get_publish_dapr_smoke_event_use_case() -> PublishDaprSmokeEventUseCase:
    """Build the use case that publishes a smoke event through Dapr."""

    dapr_client = create_dapr_client(get_dapr_client_settings())
    return PublishDaprSmokeEventUseCase(
        publisher=DaprHttpSmokeEventPublisher(dapr_client=dapr_client),
    )
