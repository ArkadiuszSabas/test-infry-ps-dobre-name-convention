"""Durable, secret-safe connector instance configuration."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType


@dataclass(frozen=True, slots=True)
class ConnectorInstanceConfiguration:
    """Configuration values persisted for one manifest-bound connector instance."""

    connector_instance_id: str
    values: Mapping[str, str]
    api_key_salt: str | None
    api_key_hash: str | None
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "connector_instance_id", self.connector_instance_id.strip())
        object.__setattr__(
            self,
            "values",
            MappingProxyType({key.strip(): value.strip() for key, value in self.values.items()}),
        )

    @property
    def api_key_configured(self) -> bool:
        return self.api_key_salt is not None and self.api_key_hash is not None
