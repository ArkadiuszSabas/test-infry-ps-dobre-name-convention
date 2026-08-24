"""Framework-free connector authentication primitives."""

from __future__ import annotations

import hmac
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class ConnectorApiKeySet:
    """Active and next API-key material bound to a configured connector instance."""

    connector_instance_id: str
    active_key: str = field(repr=False)
    next_key: str | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if not self.connector_instance_id.strip():
            raise ValueError("connector_instance_id is required.")
        if not self.active_key:
            raise ValueError("active connector API key is required.")
        if self.next_key == "":
            object.__setattr__(self, "next_key", None)

    def accepts(self, provided_key: str | None) -> bool:
        """Return whether provided key matches active or next key material."""

        if not provided_key:
            return False
        return _constant_time_equal(provided_key, self.active_key) or (
            self.next_key is not None and _constant_time_equal(provided_key, self.next_key)
        )


def _constant_time_equal(left: str, right: str) -> bool:
    return hmac.compare_digest(left.encode("utf-8"), right.encode("utf-8"))
