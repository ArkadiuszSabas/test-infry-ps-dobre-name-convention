"""Dependency factories for the worker-owned Dapr smoke slice."""

from collections.abc import Callable

from docmind_worker.application.dapr_smoke.ports import DaprSmokeEventStore
from docmind_worker.application.dapr_smoke.service import DaprSmokeEventConsumer

DaprSmokeEventConsumerDependency = Callable[[], DaprSmokeEventConsumer]


def build_dapr_smoke_event_consumer_dependency(
    *,
    store: DaprSmokeEventStore,
) -> DaprSmokeEventConsumerDependency:
    """Build an app-lifetime dependency for Dapr smoke event consumption."""

    def get_dapr_smoke_event_consumer() -> DaprSmokeEventConsumer:
        return DaprSmokeEventConsumer(store=store)

    return get_dapr_smoke_event_consumer
