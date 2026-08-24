"""Domain models for worker service discovery metadata."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ServiceInfo:
    """Stable service identity metadata."""

    service_name: str
    title: str
