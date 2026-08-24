"""Framework-free global document approval settings."""

from dataclasses import dataclass
from datetime import datetime

DOCUMENT_APPROVAL_SETTINGS_SCHEMA_VERSION = 1
DEFAULT_REQUIRED_APPROVALS = 2


@dataclass(frozen=True, slots=True)
class DocumentApprovalSettings:
    """Validated global settings snapshotted by new approval workflows."""

    required_approvals: int
    schema_version: int = DOCUMENT_APPROVAL_SETTINGS_SCHEMA_VERSION
    updated_at: datetime | None = None
    updated_by_actor_id: str | None = None

    def __post_init__(self) -> None:
        if self.schema_version != DOCUMENT_APPROVAL_SETTINGS_SCHEMA_VERSION:
            raise ValueError("Document approval settings schema_version must be 1.")
        if isinstance(self.required_approvals, bool) or self.required_approvals not in (
            1,
            2,
        ):
            raise ValueError("Document approval requires one or two reviewers.")
        if self.updated_by_actor_id is not None:
            normalized_actor_id = self.updated_by_actor_id.strip()
            if not normalized_actor_id:
                raise ValueError("Document approval settings actor id cannot be blank.")
            object.__setattr__(self, "updated_by_actor_id", normalized_actor_id)


def default_document_approval_settings() -> DocumentApprovalSettings:
    """Return the stable product default used before an override is saved."""

    return DocumentApprovalSettings(required_approvals=DEFAULT_REQUIRED_APPROVALS)
