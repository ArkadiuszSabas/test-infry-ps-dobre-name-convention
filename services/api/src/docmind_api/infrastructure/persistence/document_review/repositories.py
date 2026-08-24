"""PostgreSQL repository for versioned document Review snapshots."""

from collections.abc import Mapping, Sequence
from dataclasses import replace
from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID, uuid4

from sqlalchemy import insert, select, update
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.ext.asyncio import AsyncSession

from docmind_api.application.document_review.errors import DocumentApprovalDecisionRejectedError
from docmind_api.application.document_review.read_models import (
    DocumentReviewAttribute,
    DocumentReviewAttributeKind,
    DocumentReviewAttributeSource,
    DocumentReviewAttributeStatus,
    DocumentReviewConsistency,
    DocumentReviewConsistencyAlternative,
    DocumentReviewConsistencyOccurrence,
    DocumentReviewConsistencyStatus,
    DocumentReviewCoordinateSystem,
    DocumentReviewDataSource,
    DocumentReviewHistoryItem,
    DocumentReviewProcessingStatus,
    DocumentReviewResult,
    DocumentReviewValidation,
    DocumentReviewValueSource,
)
from docmind_api.domain.attributes.models import AttributeDataType
from docmind_api.domain.documents.approval import (
    DocumentApprovalDecision,
    DocumentApprovalDecisionRecord,
    DocumentApprovalStep,
    DocumentApprovalStepStatus,
    DocumentApprovalWorkflow,
    DocumentApprovalWorkflowError,
    DocumentApprovalWorkflowStatus,
)
from docmind_api.infrastructure.persistence.auth.tables import users_table
from docmind_api.infrastructure.persistence.document_review.tables import (
    document_approval_decisions_table,
    document_approval_workflows_table,
    document_review_versions_table,
    document_reviews_table,
)
from docmind_api.infrastructure.persistence.documents.tables import documents_table


class SqlAlchemyDocumentReviewRepository:
    """Store each Review version as an immutable JSON snapshot."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_current(self, document_id: UUID) -> DocumentReviewResult | None:
        statement = (
            select(document_reviews_table, document_review_versions_table)
            .join(
                document_review_versions_table,
                (document_review_versions_table.c.review_id == document_reviews_table.c.id)
                & (
                    document_review_versions_table.c.version
                    == document_reviews_table.c.current_version
                ),
            )
            .where(document_reviews_table.c.document_id == document_id)
        )
        row = (await self._session.execute(statement)).mappings().one_or_none()
        return _result_from_row(cast(Mapping[str, Any], row)) if row is not None else None

    async def get_version(self, document_id: UUID, version: int) -> DocumentReviewResult | None:
        statement = (
            select(document_reviews_table, document_review_versions_table)
            .join(
                document_review_versions_table,
                document_review_versions_table.c.review_id == document_reviews_table.c.id,
            )
            .where(
                document_reviews_table.c.document_id == document_id,
                document_review_versions_table.c.version == version,
            )
        )
        row = (await self._session.execute(statement)).mappings().one_or_none()
        return _result_from_row(cast(Mapping[str, Any], row)) if row is not None else None

    async def list_history(
        self,
        document_id: UUID,
        *,
        limit: int,
        offset: int,
    ) -> tuple[DocumentReviewHistoryItem, ...]:
        statement = (
            select(
                document_review_versions_table.c.version,
                document_review_versions_table.c.data_source,
                document_review_versions_table.c.quality_score,
                document_review_versions_table.c.attributes,
                document_review_versions_table.c.created_at,
                document_review_versions_table.c.created_by_actor_id,
            )
            .join(
                document_reviews_table,
                document_reviews_table.c.id == document_review_versions_table.c.review_id,
            )
            .where(document_reviews_table.c.document_id == document_id)
            .order_by(document_review_versions_table.c.version.desc())
            .limit(limit)
            .offset(offset)
        )
        rows = (await self._session.execute(statement)).mappings()
        return tuple(
            DocumentReviewHistoryItem(
                version=int(row["version"]),
                data_source=DocumentReviewDataSource(str(row["data_source"])),
                quality_score=float(row["quality_score"])
                if row["quality_score"] is not None
                else None,
                field_count=len(_json_list(row["attributes"])),
                created_at=row["created_at"],
                created_by_actor_id=row["created_by_actor_id"],
            )
            for row in rows
        )

    async def initialize(self, result: DocumentReviewResult) -> bool:
        if result.review_id is None or result.version != 1 or result.created_at is None:
            raise ValueError("Initial Review must have id, timestamp, and version 1.")
        inserted = await self._session.execute(
            postgresql_insert(document_reviews_table)
            .values(
                id=result.review_id,
                document_id=result.document_id,
                current_version=1,
                created_at=result.created_at,
                updated_at=result.updated_at or result.created_at,
            )
            .on_conflict_do_nothing(index_elements=[document_reviews_table.c.document_id])
            .returning(document_reviews_table.c.id),
        )
        if inserted.scalar_one_or_none() is None:
            return False
        await self._insert_version(result)
        return True

    async def save_next(self, *, result: DocumentReviewResult, expected_version: int) -> bool:
        if result.review_id is None or result.version != expected_version + 1:
            raise ValueError("Next Review version is inconsistent with expected_version.")
        statement = (
            update(document_reviews_table)
            .where(
                document_reviews_table.c.id == result.review_id,
                document_reviews_table.c.current_version == expected_version,
            )
            .values(current_version=result.version, updated_at=result.updated_at)
            .returning(document_reviews_table.c.id)
        )
        changed = (await self._session.execute(statement)).scalar_one_or_none()
        if changed is None:
            return False
        await self._insert_version(result)
        return True

    async def _insert_version(self, result: DocumentReviewResult) -> None:
        if result.review_id is None or result.version is None or result.updated_at is None:
            raise ValueError("Persisted Review version is incomplete.")
        await self._session.execute(
            insert(document_review_versions_table).values(
                review_id=result.review_id,
                version=result.version,
                data_source=result.data_source.value,
                is_reprocessing=result.is_reprocessing,
                source_pipeline_run_id=result.source_pipeline_run_id,
                attributes=[_attribute_to_json(field) for field in result.attributes],
                validations=[_validation_to_json(item) for item in result.validations],
                quality_score=result.quality_score,
                created_by_actor_id=result.updated_by_actor_id,
                created_at=result.updated_at,
            ),
        )


class SqlAlchemyDocumentApprovalWorkflowRepository:
    """Persist configurable approval workflows and append-only history."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, document_id: UUID) -> DocumentApprovalWorkflow | None:
        workflow = (
            (
                await self._session.execute(
                    select(document_approval_workflows_table).where(
                        document_approval_workflows_table.c.document_id == document_id
                    )
                )
            )
            .mappings()
            .one_or_none()
        )
        if workflow is None:
            return None
        decisions = (
            await self._session.execute(
                select(document_approval_decisions_table)
                .where(document_approval_decisions_table.c.document_id == document_id)
                .order_by(
                    document_approval_decisions_table.c.decided_at.desc(),
                    document_approval_decisions_table.c.run_number.desc(),
                    document_approval_decisions_table.c.step_number.desc(),
                )
                .limit(200)
            )
        ).mappings()
        parsed = _approval_workflow_from_rows(
            cast(Mapping[str, Any], workflow),
            tuple(reversed(tuple(cast(Mapping[str, Any], row) for row in decisions))),
        )
        return await self._with_reviewer_display_names(parsed)

    async def _with_reviewer_display_names(
        self, workflow: DocumentApprovalWorkflow
    ) -> DocumentApprovalWorkflow:
        actor_ids = {
            actor_id
            for actor_id in (
                *(step.reviewer_actor_id for step in workflow.steps),
                *(item.actor_id for item in workflow.history),
            )
            if actor_id is not None
        }
        user_ids: list[UUID] = []
        for actor_id in actor_ids:
            try:
                user_ids.append(UUID(actor_id))
            except ValueError:
                continue
        if not user_ids:
            return workflow
        statement = select(users_table.c.id, users_table.c.display_name).where(
            users_table.c.id.in_(user_ids)
        )
        rows = await self._session.execute(statement)
        names = {str(row.id): str(row.display_name) for row in rows}
        return replace(
            workflow,
            steps=tuple(
                replace(
                    step,
                    reviewer_display_name=(
                        names.get(step.reviewer_actor_id)
                        if step.reviewer_actor_id is not None
                        else None
                    ),
                )
                for step in workflow.steps
            ),
            history=tuple(
                replace(item, actor_display_name=names.get(item.actor_id))
                for item in workflow.history
            ),
        )

    async def initialize(
        self,
        document_id: UUID,
        *,
        required_approvals: int = 2,
    ) -> DocumentApprovalWorkflow:
        """Create a waiting workflow and synchronize the document Inbox status once."""

        if isinstance(required_approvals, bool) or required_approvals not in (1, 2):
            raise ValueError("Document approval requires one or two reviewers.")

        document = await self._session.scalar(
            select(documents_table.c.id)
            .where(documents_table.c.id == document_id)
            .with_for_update()
        )
        if document is None:
            raise DocumentApprovalDecisionRejectedError(
                code="DOCUMENT_APPROVAL_DOCUMENT_NOT_FOUND",
                message="The document cannot be approved because it does not exist.",
            )
        review_version = await self._session.scalar(
            select(document_reviews_table.c.current_version).where(
                document_reviews_table.c.document_id == document_id
            )
        )
        if review_version is None:
            raise DocumentApprovalDecisionRejectedError(
                code="DOCUMENT_APPROVAL_REVIEW_NOT_INITIALIZED",
                message="The document Review must be initialized before approval begins.",
            )
        now = datetime.now(tz=UTC)
        inserted = await self._session.execute(
            postgresql_insert(document_approval_workflows_table)
            .values(
                document_id=document_id,
                current_run=1,
                review_version=review_version,
                required_approvals=required_approvals,
                status=DocumentApprovalWorkflowStatus.WAITING_FOR_REVIEW.value,
                updated_at=now,
            )
            .on_conflict_do_nothing(
                index_elements=[document_approval_workflows_table.c.document_id]
            )
            .returning(document_approval_workflows_table.c.document_id)
        )
        if inserted.scalar_one_or_none() is not None:
            await self._session.execute(
                update(documents_table)
                .where(documents_table.c.id == document_id)
                .values(
                    status=DocumentApprovalWorkflowStatus.WAITING_FOR_REVIEW.value, updated_at=now
                )
            )
        workflow = await self.get(document_id)
        if workflow is None:
            raise RuntimeError("Approval workflow initialization did not persist.")
        return workflow

    async def reset_for_review_version(
        self,
        *,
        document_id: UUID,
        review_version: int,
    ) -> DocumentApprovalWorkflow:
        """Reset approval under the document lock before persisting a new Review version."""

        document = await self._session.scalar(
            select(documents_table.c.id)
            .where(documents_table.c.id == document_id)
            .with_for_update()
        )
        if document is None:
            raise DocumentApprovalDecisionRejectedError(
                code="DOCUMENT_APPROVAL_DOCUMENT_NOT_FOUND",
                message="The document cannot be approved because it does not exist.",
            )
        workflow = await self.get(document_id)
        if workflow is None:
            raise DocumentApprovalDecisionRejectedError(
                code="DOCUMENT_APPROVAL_WORKFLOW_NOT_INITIALIZED",
                message="The document approval workflow must be initialized before saving Review.",
            )
        now = datetime.now(tz=UTC)
        await self._session.execute(
            update(document_approval_workflows_table)
            .where(document_approval_workflows_table.c.document_id == document_id)
            .values(
                current_run=workflow.run_number + 1,
                review_version=review_version,
                status=DocumentApprovalWorkflowStatus.WAITING_FOR_REVIEW.value,
                updated_at=now,
            )
        )
        await self._session.execute(
            update(documents_table)
            .where(documents_table.c.id == document_id)
            .values(status=DocumentApprovalWorkflowStatus.WAITING_FOR_REVIEW.value, updated_at=now)
        )
        updated = await self.get(document_id)
        if updated is None:
            raise RuntimeError("Approval workflow reset did not persist.")
        return updated

    async def decide(
        self,
        *,
        document_id: UUID,
        actor_id: str,
        expected_review_version: int,
        decision: DocumentApprovalDecision,
        comment: str | None,
    ) -> DocumentApprovalWorkflow:
        document = await self._session.scalar(
            select(documents_table.c.id)
            .where(documents_table.c.id == document_id)
            .with_for_update()
        )
        if document is None:
            raise DocumentApprovalDecisionRejectedError(
                code="DOCUMENT_APPROVAL_DOCUMENT_NOT_FOUND",
                message="The document cannot be approved because it does not exist.",
            )
        current = await self.get(document_id)
        if current is None:
            raise DocumentApprovalDecisionRejectedError(
                code="DOCUMENT_APPROVAL_WORKFLOW_NOT_INITIALIZED",
                message="The document approval workflow must be initialized before a decision.",
            )
        review_version = await self._session.scalar(
            select(document_reviews_table.c.current_version).where(
                document_reviews_table.c.document_id == document_id
            )
        )
        if review_version is None:
            raise DocumentApprovalDecisionRejectedError(
                code="DOCUMENT_APPROVAL_REVIEW_NOT_INITIALIZED",
                message="The document Review must be initialized before approval begins.",
            )
        if review_version != expected_review_version:
            raise DocumentApprovalDecisionRejectedError(
                code="DOCUMENT_APPROVAL_REVIEW_VERSION_CONFLICT",
                message="The document Review changed before the approval decision was recorded.",
            )
        if current.review_version != review_version:
            raise DocumentApprovalDecisionRejectedError(
                code="DOCUMENT_APPROVAL_REVIEW_VERSION_MISMATCH",
                message="Approval must be reset for the current Review version.",
            )
        now = datetime.now(tz=UTC)
        try:
            record, next_workflow = current.decide(
                actor_id=actor_id,
                decision=decision,
                comment=comment,
                decided_at=now,
            )
        except DocumentApprovalWorkflowError as error:
            raise DocumentApprovalDecisionRejectedError(
                code=error.code,
                message=str(error),
            ) from error
        await self._session.execute(
            insert(document_approval_decisions_table).values(
                id=uuid4(),
                document_id=document_id,
                run_number=record.run_number,
                step_number=record.step_number,
                decision=record.decision.value,
                actor_id=record.actor_id,
                comment=record.comment,
                decided_at=record.decided_at,
            )
        )
        await self._session.execute(
            update(document_approval_workflows_table)
            .where(document_approval_workflows_table.c.document_id == document_id)
            .values(
                current_run=next_workflow.run_number,
                status=next_workflow.status.value,
                updated_at=now,
            )
        )
        await self._session.execute(
            update(documents_table)
            .where(documents_table.c.id == document_id)
            .values(status=next_workflow.status.value, updated_at=now)
        )
        updated = await self.get(document_id)
        if updated is None:
            raise RuntimeError("Approval workflow write did not persist.")
        return updated


def _result_from_row(row: Mapping[str, Any]) -> DocumentReviewResult:
    return DocumentReviewResult(
        schema_version=2,
        review_id=row["id"],
        document_id=row["document_id"],
        version=int(row["version"]),
        data_source=DocumentReviewDataSource(str(row["data_source"])),
        processing_status=(
            DocumentReviewProcessingStatus.PENDING
            if row["is_reprocessing"]
            else DocumentReviewProcessingStatus.COMPLETED
        ),
        attributes_available=not row["is_reprocessing"],
        unavailable_reason_code=("REVIEW_REPROCESSING_PENDING" if row["is_reprocessing"] else None),
        source_pipeline_run_id=row["source_pipeline_run_id"],
        quality_score=float(row["quality_score"]) if row["quality_score"] is not None else None,
        validations=tuple(
            _validation_from_json(item) for item in _json_mappings(row["validations"])
        ),
        attributes=tuple(_attribute_from_json(item) for item in _json_mappings(row["attributes"])),
        created_at=row["created_at"],
        updated_at=row["created_at_1"],
        updated_by_actor_id=row["created_by_actor_id"],
        is_reprocessing=bool(row["is_reprocessing"]),
    )


def _attribute_to_json(field: DocumentReviewAttribute) -> dict[str, object]:
    return {
        "id": str(field.id),
        "kind": field.kind.value,
        "attribute_id": str(field.attribute_id) if field.attribute_id is not None else None,
        "attribute_external_id": field.attribute_external_id,
        "label": field.label,
        "data_type": field.data_type.value,
        "required": field.required,
        "display_order": field.display_order,
        "value": field.value,
        "display_value": field.display_value,
        "confidence": field.confidence,
        "status": field.status.value,
        "requires_review": field.requires_review,
        "review_reason_codes": list(field.review_reason_codes),
        "sources": [_source_to_json(source) for source in field.sources],
        "consistency": _consistency_to_json(field.consistency),
        "value_source": field.value_source.value,
        "manually_edited": field.manually_edited,
    }


def _attribute_from_json(value: Mapping[str, Any]) -> DocumentReviewAttribute:
    attribute_id = value.get("attribute_id")
    return DocumentReviewAttribute(
        id=UUID(str(value["id"])),
        kind=DocumentReviewAttributeKind(str(value["kind"])),
        attribute_id=UUID(str(attribute_id)) if attribute_id is not None else None,
        attribute_external_id=cast(str | None, value.get("attribute_external_id")),
        label=str(value["label"]),
        data_type=AttributeDataType(str(value["data_type"])),
        required=bool(value["required"]),
        display_order=int(value["display_order"]),
        value=cast(str | None, value.get("value")),
        display_value=cast(str | None, value.get("display_value")),
        confidence=float(value["confidence"]) if value.get("confidence") is not None else None,
        status=DocumentReviewAttributeStatus(str(value["status"])),
        requires_review=bool(value["requires_review"]),
        review_reason_codes=tuple(str(item) for item in _json_list(value["review_reason_codes"])),
        sources=tuple(_source_from_json(item) for item in _json_mappings(value["sources"])),
        consistency=_consistency_from_json(value.get("consistency")),
        value_source=DocumentReviewValueSource(str(value["value_source"])),
        manually_edited=bool(value["manually_edited"]),
    )


def _consistency_to_json(consistency: DocumentReviewConsistency) -> dict[str, object]:
    return {
        "status": consistency.status.value,
        "occurrence_count": consistency.occurrence_count,
        "confidence_before": consistency.confidence_before,
        "confidence_after": consistency.confidence_after,
        "alternatives": [
            {
                "value": alternative.value,
                "occurrences": [
                    {
                        "page_number": occurrence.page_number,
                        "key_value_index": occurrence.key_value_index,
                    }
                    for occurrence in alternative.occurrences
                ],
            }
            for alternative in consistency.alternatives
        ],
    }


def _consistency_from_json(value: object) -> DocumentReviewConsistency:
    payload: Mapping[str, Any] = (
        cast(Mapping[str, Any], value) if isinstance(value, Mapping) else {}
    )
    try:
        status = DocumentReviewConsistencyStatus(str(payload.get("status")))
    except ValueError:
        status = DocumentReviewConsistencyStatus.NOT_AVAILABLE
    alternatives = tuple(
        DocumentReviewConsistencyAlternative(
            value=str(item["value"]),
            occurrences=tuple(
                DocumentReviewConsistencyOccurrence(
                    page_number=_positive_int_or_none(occurrence.get("page_number")),
                    key_value_index=_positive_int_or_none(occurrence.get("key_value_index")),
                )
                for occurrence in _json_mappings(item.get("occurrences"))
            ),
        )
        for item in _json_mappings(payload.get("alternatives", []))
        if isinstance(item.get("value"), str) and item["value"]
    )
    occurrence_count = payload.get("occurrence_count")
    return DocumentReviewConsistency(
        status=status,
        occurrence_count=occurrence_count
        if isinstance(occurrence_count, int) and not isinstance(occurrence_count, bool)
        else 0,
        confidence_before=_json_float_or_none(payload.get("confidence_before")),
        confidence_after=_json_float_or_none(payload.get("confidence_after")),
        alternatives=alternatives,
    )


def _source_to_json(source: DocumentReviewAttributeSource) -> dict[str, object]:
    return {
        "kind": source.kind,
        "page_number": source.page_number,
        "order_index": source.order_index,
        "coordinate_system": source.coordinate_system.value,
        "bounding_polygon": (
            list(source.bounding_polygon) if source.bounding_polygon is not None else None
        ),
        "confidence": source.confidence,
        "source_key": source.source_key,
    }


def _source_from_json(value: Mapping[str, Any]) -> DocumentReviewAttributeSource:
    return DocumentReviewAttributeSource(
        kind=str(value["kind"]),
        page_number=int(value["page_number"]),
        order_index=int(value["order_index"]),
        coordinate_system=DocumentReviewCoordinateSystem(str(value["coordinate_system"])),
        bounding_polygon=(
            tuple(_json_float(item) for item in _json_list(value["bounding_polygon"]))
            if value.get("bounding_polygon") is not None
            else None
        ),
        confidence=float(value["confidence"]) if value.get("confidence") is not None else None,
        source_key=cast(str | None, value.get("source_key")),
    )


def _validation_to_json(item: DocumentReviewValidation) -> dict[str, object]:
    return {
        "code": item.code,
        "severity": item.severity,
        "field_id": str(item.field_id) if item.field_id is not None else None,
        "message": item.message,
    }


def _validation_from_json(value: Mapping[str, Any]) -> DocumentReviewValidation:
    field_id = value.get("field_id")
    return DocumentReviewValidation(
        code=str(value["code"]),
        severity=str(value["severity"]),
        field_id=UUID(str(field_id)) if field_id is not None else None,
        message=str(value["message"]),
    )


def _json_list(value: object) -> list[object]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise ValueError("Stored Review JSON value must be an array.")
    return list(cast(Sequence[object], value))


def _json_mappings(value: object) -> tuple[Mapping[str, Any], ...]:
    result: list[Mapping[str, Any]] = []
    for item in _json_list(value):
        if not isinstance(item, Mapping):
            raise ValueError("Stored Review JSON array entries must be objects.")
        result.append(cast(Mapping[str, Any], item))
    return tuple(result)


def _json_float(value: object) -> float:
    if not isinstance(value, int | float):
        raise ValueError("Stored Review coordinate must be numeric.")
    return float(value)


def _json_float_or_none(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    numeric = float(value)
    return numeric if 0 <= numeric <= 1 else None


def _positive_int_or_none(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        return None
    return value


def _approval_workflow_from_rows(
    workflow: Mapping[str, Any], rows: tuple[Mapping[str, Any], ...]
) -> DocumentApprovalWorkflow:
    run = int(workflow["current_run"])
    required_approvals = int(workflow["required_approvals"])
    history = tuple(
        DocumentApprovalDecisionRecord(
            int(row["run_number"]),
            int(row["step_number"]),
            DocumentApprovalDecision(str(row["decision"])),
            str(row["actor_id"]),
            cast(str | None, row["comment"]),
            row["decided_at"],
        )
        for row in rows
    )
    current = tuple(item for item in history if item.run_number == run)
    approved = {
        item.step_number: item
        for item in current
        if item.decision is DocumentApprovalDecision.APPROVED
    }
    steps = tuple(
        DocumentApprovalStep(
            number,
            DocumentApprovalStepStatus.APPROVED
            if number in approved
            else DocumentApprovalStepStatus.WAITING,
            approved[number].actor_id if number in approved else None,
            approved[number].decided_at if number in approved else None,
            approved[number].comment if number in approved else None,
        )
        for number in range(1, required_approvals + 1)
    )
    return DocumentApprovalWorkflow(
        run,
        DocumentApprovalWorkflowStatus(str(workflow["status"])),
        steps,
        history,
        int(workflow["review_version"]),
        required_approvals,
    )
