import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import NAMESPACE_URL, UUID, uuid5

from docmind_api.domain.attributes.models import normalize_attribute_external_id
from docmind_api.domain.document_types.models import normalize_document_type_external_id

_ATTRIBUTE_REQUIREMENT_EXTERNAL_ID_PATTERN = re.compile(r"^[a-z][a-z0-9]*(_[a-z0-9]+)*$")


class MissingRequiredAttributeAction(StrEnum):
    """Supported actions when a required attribute value is missing."""

    BLOCK_APPROVAL = "block_approval"
    REQUIRE_REVIEW = "require_review"


@dataclass(frozen=True, slots=True, init=False)
class DocumentTypeAttributeRequirement:
    """Requirement configuration for one attribute within one document type."""

    id: UUID
    external_id: str
    document_type_id: UUID
    attribute_definition_id: UUID
    required: bool
    include_metadata_in_context_resolver: bool
    missing_required_action: MissingRequiredAttributeAction | None
    created_at: datetime
    updated_at: datetime

    def __init__(
        self,
        *,
        document_type_id: UUID | str,
        required: bool,
        missing_required_action: MissingRequiredAttributeAction | None,
        created_at: datetime,
        updated_at: datetime,
        attribute_definition_id: UUID | str | None = None,
        attribute_id: UUID | str | None = None,
        id: UUID | str | None = None,
        external_id: str | None = None,
        include_metadata_in_context_resolver: bool = False,
    ) -> None:
        attribute_reference = (
            attribute_definition_id if attribute_definition_id is not None else attribute_id
        )
        if attribute_reference is None:
            raise ValueError("Attribute definition ID is required.")

        normalized_document_type_id = _normalize_uuid_or_external(
            document_type_id,
            prefix="document-type",
            normalizer=normalize_document_type_external_id,
        )
        normalized_attribute_id = _normalize_uuid_or_external(
            attribute_reference,
            prefix="attribute-definition",
            normalizer=normalize_attribute_external_id,
        )
        normalized_external_id = external_id or _derived_requirement_external_id(
            document_type_id,
            attribute_reference,
            id,
        )
        normalized_id = (
            UUID(str(id))
            if id is not None
            else uuid5(
                NAMESPACE_URL,
                f"docmind:attribute-requirement:{normalized_external_id}",
            )
        )

        object.__setattr__(self, "id", normalized_id)
        object.__setattr__(
            self,
            "external_id",
            normalize_attribute_requirement_external_id(normalized_external_id),
        )
        object.__setattr__(
            self,
            "document_type_id",
            normalized_document_type_id,
        )
        object.__setattr__(
            self,
            "attribute_definition_id",
            normalized_attribute_id,
        )
        object.__setattr__(self, "required", required)
        object.__setattr__(
            self, "include_metadata_in_context_resolver", include_metadata_in_context_resolver
        )
        object.__setattr__(self, "missing_required_action", missing_required_action)
        object.__setattr__(self, "created_at", created_at)
        object.__setattr__(self, "updated_at", updated_at)
        if self.required and self.missing_required_action is None:
            raise ValueError("Required attributes must define a missing-required action.")
        if not self.required and self.missing_required_action is not None:
            raise ValueError("Optional attributes must not define a missing-required action.")
        if self.created_at > self.updated_at:
            raise ValueError("Attribute requirement updated_at cannot be before created_at.")

    @property
    def attribute_id(self) -> UUID:
        """Return the selected attribute definition UUID."""

        return self.attribute_definition_id


def normalize_attribute_requirement_external_id(value: str) -> str:
    """Validate and return a stable snake_case requirement business id."""

    normalized = value.strip()
    if not normalized:
        raise ValueError("Attribute requirement external_id is required.")
    if _ATTRIBUTE_REQUIREMENT_EXTERNAL_ID_PATTERN.fullmatch(normalized) is None:
        raise ValueError("Attribute requirement external_id must be snake_case.")

    return normalized


def _normalize_uuid_or_external(
    value: UUID | str,
    *,
    prefix: str,
    normalizer: Callable[[str], str],
) -> UUID:
    try:
        return UUID(str(value))
    except ValueError:
        external_id = normalizer(str(value))
        return uuid5(NAMESPACE_URL, f"docmind:{prefix}:{external_id}")


def _derived_requirement_external_id(
    document_type_id: UUID | str,
    attribute_reference: UUID | str,
    requirement_id: UUID | str | None,
) -> str:
    try:
        document_type_external_id = normalize_document_type_external_id(str(document_type_id))
        attribute_external_id = normalize_attribute_external_id(str(attribute_reference))
    except ValueError:
        if requirement_id is None:
            return (
                "requirement_"
                + uuid5(
                    NAMESPACE_URL,
                    f"docmind:attribute-requirement:{document_type_id}:{attribute_reference}",
                ).hex
            )
        return "requirement_" + UUID(str(requirement_id)).hex

    return _stable_requirement_external_id(
        document_type_external_id=document_type_external_id,
        attribute_external_id=attribute_external_id,
    )


def _stable_requirement_external_id(
    *,
    document_type_external_id: str,
    attribute_external_id: str,
) -> str:
    return (
        "requirement_"
        + uuid5(
            NAMESPACE_URL,
            (f"docmind:attribute-requirement:{document_type_external_id}:{attribute_external_id}"),
        ).hex
    )
