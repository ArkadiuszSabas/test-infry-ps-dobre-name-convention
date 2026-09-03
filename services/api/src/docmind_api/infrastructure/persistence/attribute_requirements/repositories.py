"""Document type attribute requirement repository implementations."""

from collections.abc import Mapping
from typing import Any
from uuid import UUID

from sqlalchemy import delete, select, text
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.ext.asyncio import AsyncSession

from docmind_api.application.attribute_requirements.ports import (
    AttributeRequirementRepository,
)
from docmind_api.domain.attribute_requirements.models import (
    DocumentTypeAttributeRequirement,
    MissingRequiredAttributeAction,
)
from docmind_api.infrastructure.persistence.attribute_requirements.tables import (
    attribute_requirements_table,
)
from docmind_api.infrastructure.persistence.document_types.tables import document_types_table


class SqlAlchemyAttributeRequirementRepository(AttributeRequirementRepository):
    """PostgreSQL-backed attribute requirement matrix repository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def lock_matrix_writes(self) -> None:
        """Serialize all attribute-requirement matrix writes in this transaction.

        Both public writers can replace rows that the other writer owns. A single
        transaction-scoped advisory lock therefore prevents a document-type save
        from deleting an assignment that an attribute-centric save just created.
        """
        await self._session.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:key))"),
            {"key": "docmind:attribute-requirements:matrix-write"},
        )

    async def list_for_document_type(
        self,
        document_type_id: UUID | str,
    ) -> tuple[DocumentTypeAttributeRequirement, ...]:
        """Return requirement rows for one document type."""

        normalized_document_type_id = await self._resolve_document_type_id(document_type_id)
        if normalized_document_type_id is None:
            return ()

        statement = (
            select(attribute_requirements_table)
            .where(
                attribute_requirements_table.c.document_type_id == normalized_document_type_id,
            )
            .order_by(attribute_requirements_table.c.attribute_definition_id.asc())
        )
        result = await self._session.execute(statement)
        return tuple(_requirement_from_row(row) for row in result.mappings())

    async def replace_for_document_type(
        self,
        document_type_id: UUID | str,
        requirements: tuple[DocumentTypeAttributeRequirement, ...],
    ) -> None:
        """Replace stored requirement rows for one document type."""

        normalized_document_type_id = await self._resolve_document_type_id(document_type_id)
        if normalized_document_type_id is None:
            return

        attribute_definition_ids = tuple(
            requirement.attribute_definition_id for requirement in requirements
        )
        delete_statement = delete(attribute_requirements_table).where(
            attribute_requirements_table.c.document_type_id == normalized_document_type_id,
        )
        if attribute_definition_ids:
            delete_statement = delete_statement.where(
                attribute_requirements_table.c.attribute_definition_id.not_in(
                    attribute_definition_ids,
                ),
            )
        await self._session.execute(delete_statement)

        for requirement in requirements:
            statement = postgresql_insert(
                attribute_requirements_table,
            ).values(
                id=requirement.id,
                external_id=requirement.external_id,
                document_type_id=requirement.document_type_id,
                attribute_definition_id=requirement.attribute_definition_id,
                required=requirement.required,
                include_metadata_in_context_resolver=requirement.include_metadata_in_context_resolver,
                missing_required_action=(
                    requirement.missing_required_action.value
                    if requirement.missing_required_action is not None
                    else None
                ),
                created_at=requirement.created_at,
                updated_at=requirement.updated_at,
            )
            await self._session.execute(
                statement.on_conflict_do_update(
                    index_elements=[
                        attribute_requirements_table.c.document_type_id,
                        attribute_requirements_table.c.attribute_definition_id,
                    ],
                    set_={
                        "external_id": requirement.external_id,
                        "required": requirement.required,
                        "include_metadata_in_context_resolver": (
                            requirement.include_metadata_in_context_resolver
                        ),
                        "missing_required_action": (
                            requirement.missing_required_action.value
                            if requirement.missing_required_action is not None
                            else None
                        ),
                        "updated_at": requirement.updated_at,
                    },
                ),
            )

    async def list_for_attribute(
        self, attribute_definition_id: UUID | str, *, for_update: bool = False
    ) -> tuple[DocumentTypeAttributeRequirement, ...]:
        """Return assignments for one attribute without loading document matrices."""
        statement = (
            select(attribute_requirements_table)
            .where(
                attribute_requirements_table.c.attribute_definition_id
                == UUID(str(attribute_definition_id))
            )
            .order_by(attribute_requirements_table.c.document_type_id.asc())
        )
        result = await self._session.execute(
            statement.with_for_update() if for_update else statement
        )
        return tuple(_requirement_from_row(row) for row in result.mappings())

    async def replace_for_attribute(
        self,
        attribute_definition_id: UUID,
        requirements: tuple[DocumentTypeAttributeRequirement, ...],
    ) -> None:
        await self._session.execute(
            delete(attribute_requirements_table).where(
                attribute_requirements_table.c.attribute_definition_id == attribute_definition_id,
            )
        )
        for requirement in requirements:
            await self._session.execute(
                postgresql_insert(attribute_requirements_table).values(
                    id=requirement.id,
                    external_id=requirement.external_id,
                    document_type_id=requirement.document_type_id,
                    attribute_definition_id=requirement.attribute_definition_id,
                    required=requirement.required,
                    include_metadata_in_context_resolver=requirement.include_metadata_in_context_resolver,
                    missing_required_action=(
                        requirement.missing_required_action.value
                        if requirement.missing_required_action
                        else None
                    ),
                    created_at=requirement.created_at,
                    updated_at=requirement.updated_at,
                )
            )

    async def _resolve_document_type_id(self, document_type_id: UUID | str) -> UUID | None:
        try:
            return UUID(str(document_type_id))
        except ValueError:
            statement = select(document_types_table.c.id).where(
                document_types_table.c.external_id == str(document_type_id),
            )
            return await self._session.scalar(statement)


def _requirement_from_row(row: Mapping[Any, Any]) -> DocumentTypeAttributeRequirement:
    missing_required_action = row["missing_required_action"]
    return DocumentTypeAttributeRequirement(
        id=row["id"],
        external_id=row["external_id"],
        document_type_id=row["document_type_id"],
        attribute_definition_id=row["attribute_definition_id"],
        required=row["required"],
        include_metadata_in_context_resolver=row["include_metadata_in_context_resolver"],
        missing_required_action=(
            MissingRequiredAttributeAction(missing_required_action)
            if missing_required_action is not None
            else None
        ),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )
