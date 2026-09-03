"""Select persisted Context Resolver results for Review initialization."""

from collections.abc import Mapping
from dataclasses import replace
from typing import cast
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from docmind_api.application.document_review.read_models import DocumentReviewResult
from docmind_api.domain.ocr_pipeline_runs.models import OcrPipelineRunStatus
from docmind_api.infrastructure.document_review.context_resolution_mapper import (
    review_result_from_context_resolution_payload,
)
from docmind_api.infrastructure.persistence.attribute_requirements.tables import (
    attribute_requirements_table,
)
from docmind_api.infrastructure.persistence.attributes.tables import (
    attribute_categories_table,
    attribute_definitions_table,
)
from docmind_api.infrastructure.persistence.documents.tables import documents_table
from docmind_api.infrastructure.persistence.ocr_pipeline_runs.tables import (
    ocr_pipeline_runs_table,
)

_ELIGIBLE_RUN_STATUSES = (
    OcrPipelineRunStatus.SUCCEEDED.value,
    OcrPipelineRunStatus.PARTIAL_FAILED.value,
)


class SqlAlchemyDocumentReviewPipelineSource:
    """Return the oldest usable Context Resolver result for one document."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_first_eligible(self, document_id: UUID) -> DocumentReviewResult | None:
        """Select the oldest terminal run whose payload can initialize Review."""

        statement = (
            select(
                ocr_pipeline_runs_table.c.id,
                ocr_pipeline_runs_table.c.result_payload,
                documents_table.c.document_type_id,
            )
            .join(
                documents_table,
                documents_table.c.id == ocr_pipeline_runs_table.c.document_id,
            )
            .where(
                ocr_pipeline_runs_table.c.document_id == document_id,
                ocr_pipeline_runs_table.c.status.in_(_ELIGIBLE_RUN_STATUSES),
                ocr_pipeline_runs_table.c.result_payload.is_not(None),
            )
            .order_by(
                ocr_pipeline_runs_table.c.created_at.asc(),
                ocr_pipeline_runs_table.c.id.asc(),
            )
        )
        rows = (await self._session.execute(statement)).mappings()
        for row in rows:
            payload = _mapping_or_none(row["result_payload"])
            if payload is None:
                continue
            result = review_result_from_context_resolution_payload(
                document_id=document_id,
                payload=payload,
                source_pipeline_run_id=cast(UUID, row["id"]),
            )
            if result.attributes_available:
                return await self._exclude_metadata_attributes(
                    result,
                    document_type_id=cast(UUID, row["document_type_id"]),
                )
        return None

    async def get_for_run(
        self,
        document_id: UUID,
        run_id: UUID,
    ) -> DocumentReviewResult | None:
        """Return one eligible Context Resolver result for the specified run."""

        statement = (
            select(
                ocr_pipeline_runs_table.c.id,
                ocr_pipeline_runs_table.c.result_payload,
                documents_table.c.document_type_id,
            )
            .join(
                documents_table,
                documents_table.c.id == ocr_pipeline_runs_table.c.document_id,
            )
            .where(
                ocr_pipeline_runs_table.c.id == run_id,
                ocr_pipeline_runs_table.c.document_id == document_id,
                ocr_pipeline_runs_table.c.status.in_(_ELIGIBLE_RUN_STATUSES),
                ocr_pipeline_runs_table.c.result_payload.is_not(None),
            )
        )
        row = (await self._session.execute(statement)).mappings().one_or_none()
        if row is None:
            return None
        payload = _mapping_or_none(row["result_payload"])
        if payload is None:
            return None
        result = review_result_from_context_resolution_payload(
            document_id=document_id,
            payload=payload,
            source_pipeline_run_id=run_id,
        )
        if not result.attributes_available:
            return None
        return await self._exclude_metadata_attributes(
            result,
            document_type_id=cast(UUID, row["document_type_id"]),
        )

    async def _exclude_metadata_attributes(
        self,
        result: DocumentReviewResult,
        *,
        document_type_id: UUID,
    ) -> DocumentReviewResult:
        attribute_ids = {attribute.attribute_id for attribute in result.attributes}
        configured_attribute_ids = {attribute_id for attribute_id in attribute_ids if attribute_id}
        if not configured_attribute_ids:
            return result
        statement = (
            select(attribute_definitions_table.c.id)
            .join(
                attribute_categories_table,
                attribute_categories_table.c.id == attribute_definitions_table.c.category_id,
            )
            .outerjoin(
                attribute_requirements_table,
                and_(
                    attribute_requirements_table.c.attribute_definition_id
                    == attribute_definitions_table.c.id,
                    attribute_requirements_table.c.document_type_id == document_type_id,
                ),
            )
            .where(
                attribute_definitions_table.c.id.in_(configured_attribute_ids),
                attribute_categories_table.c.status == "active",
                attribute_categories_table.c.flags["isMetadata"].astext == "true",
                attribute_requirements_table.c.include_metadata_in_context_resolver.is_not(True),
            )
        )
        metadata_attribute_ids = set((await self._session.scalars(statement)).all())
        if not metadata_attribute_ids:
            return result
        return replace(
            result,
            attributes=tuple(
                attribute
                for attribute in result.attributes
                if attribute.attribute_id not in metadata_attribute_ids
            ),
        )


def _mapping_or_none(value: object) -> Mapping[str, object] | None:
    if not isinstance(value, Mapping):
        return None
    return cast(Mapping[str, object], value)
