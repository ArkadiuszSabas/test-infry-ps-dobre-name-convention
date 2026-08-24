"""Document type catalog domain models and invariants."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import NAMESPACE_URL, UUID, uuid5

DOCUMENT_TYPE_ID_MAX_LENGTH = 80
DOCUMENT_TYPE_NAME_MAX_LENGTH = 200
DOCUMENT_TYPE_DESCRIPTION_MAX_LENGTH = 2000


class DocumentTypeStatus(StrEnum):
    """Lifecycle status for catalog document types."""

    ACTIVE = "active"
    INACTIVE = "inactive"


@dataclass(frozen=True, slots=True)
class DocumentTypeUsage:
    """Blocking dependency counts for a document type."""

    attribute_mappings: int = 0
    active_workflows: int = 0
    classification_rules: int = 0
    historical_documents: int = 0

    def __post_init__(self) -> None:
        for field_name, value in self.as_details().items():
            if value < 0:
                raise ValueError(f"{field_name} cannot be negative.")

    @property
    def has_blocking_dependencies(self) -> bool:
        """Return whether this usage prevents permanent deletion."""

        return bool(self.blocking_dependencies)

    @property
    def blocking_dependencies(self) -> tuple[str, ...]:
        """Return dependency categories with at least one use."""

        return tuple(name for name, value in self.as_details().items() if value > 0)

    def as_details(self) -> dict[str, int]:
        """Return API-safe dependency counts."""

        return {
            "attribute_mappings": self.attribute_mappings,
            "active_workflows": self.active_workflows,
            "classification_rules": self.classification_rules,
            "historical_documents": self.historical_documents,
        }


@dataclass(frozen=True, slots=True)
class DocumentType:
    """A configured document type available to DocMind workflows."""

    id: UUID | str
    name: str
    description: str | None
    status: DocumentTypeStatus
    created_at: datetime
    updated_at: datetime
    external_id: str | None = None

    def __post_init__(self) -> None:
        raw_id = self.id
        external_id = self.external_id
        try:
            normalized_id = UUID(str(raw_id))
        except ValueError:
            if not external_id and isinstance(raw_id, str):
                external_id = raw_id
                normalized_id = uuid5(NAMESPACE_URL, f"docmind:document-type:{external_id}")
            else:
                raise
        object.__setattr__(self, "id", normalized_id)
        object.__setattr__(
            self,
            "external_id",
            (normalize_document_type_external_id(external_id) if external_id is not None else None),
        )
        object.__setattr__(self, "name", normalize_document_type_name(self.name))
        object.__setattr__(
            self,
            "description",
            normalize_document_type_description(self.description),
        )
        if self.created_at > self.updated_at:
            raise ValueError("Document type updated_at cannot be before created_at.")

    @property
    def is_active(self) -> bool:
        """Return whether the document type is available for product workflows."""

        return self.status == DocumentTypeStatus.ACTIVE

    def update_business_fields(
        self,
        *,
        external_id: str | None,
        name: str,
        description: str | None,
        updated_at: datetime,
    ) -> DocumentType:
        """Return this document type with edited business fields and stable technical fields."""

        return DocumentType(
            id=self.id,
            external_id=external_id,
            name=name,
            description=description,
            status=self.status,
            created_at=self.created_at,
            updated_at=updated_at,
        )

    def deactivate(self, *, updated_at: datetime) -> DocumentType:
        """Return this document type with inactive status and stable identity."""

        return DocumentType(
            id=self.id,
            external_id=self.external_id,
            name=self.name,
            description=self.description,
            status=DocumentTypeStatus.INACTIVE,
            created_at=self.created_at,
            updated_at=updated_at,
        )


def normalize_document_type_external_id(value: str) -> str:
    """Validate and return a stable optional document type external identifier."""

    normalized = value.strip()
    if not normalized:
        raise ValueError("Document type external_id cannot be empty.")
    if len(normalized) > DOCUMENT_TYPE_ID_MAX_LENGTH:
        raise ValueError(
            f"Document type external_id cannot exceed {DOCUMENT_TYPE_ID_MAX_LENGTH} characters.",
        )

    return normalized


def normalize_document_type_name(value: str) -> str:
    """Validate and return the display name for a document type."""

    normalized = value.strip()
    if not normalized:
        raise ValueError("Document type name is required.")
    if len(normalized) > DOCUMENT_TYPE_NAME_MAX_LENGTH:
        raise ValueError(
            f"Document type name cannot exceed {DOCUMENT_TYPE_NAME_MAX_LENGTH} characters.",
        )

    return normalized


def normalize_document_type_description(value: str | None) -> str | None:
    """Validate and return an optional document type description."""

    if value is None:
        return None

    normalized = value.strip()
    if not normalized:
        return None
    if len(normalized) > DOCUMENT_TYPE_DESCRIPTION_MAX_LENGTH:
        raise ValueError(
            "Document type description cannot exceed "
            f"{DOCUMENT_TYPE_DESCRIPTION_MAX_LENGTH} characters.",
        )

    return normalized
