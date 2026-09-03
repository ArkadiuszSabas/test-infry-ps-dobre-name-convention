"""Application ports for document type attribute requirement configuration."""

from datetime import datetime
from typing import Protocol
from uuid import UUID

from docmind_api.domain.attribute_requirements.models import (
    DocumentTypeAttributeRequirement,
)


class Clock(Protocol):
    """Port for obtaining audit timestamps."""

    def now(self) -> datetime: ...


class AttributeRequirementIdFactory(Protocol):
    """Port for creating attribute requirement identifiers."""

    def new_id(self) -> UUID: ...


class AttributeRequirementRepository(Protocol):
    """Port implemented by attribute requirement persistence adapters."""

    async def list_for_document_type(
        self,
        document_type_id: UUID | str,
    ) -> tuple[DocumentTypeAttributeRequirement, ...]: ...

    async def replace_for_document_type(
        self,
        document_type_id: UUID | str,
        requirements: tuple[DocumentTypeAttributeRequirement, ...],
    ) -> None: ...

    async def lock_matrix_writes(self) -> None: ...

    async def list_for_attribute(
        self, attribute_definition_id: UUID | str, *, for_update: bool = False
    ) -> tuple[DocumentTypeAttributeRequirement, ...]: ...

    async def replace_for_attribute(
        self,
        attribute_definition_id: UUID,
        requirements: tuple[DocumentTypeAttributeRequirement, ...],
    ) -> None: ...
