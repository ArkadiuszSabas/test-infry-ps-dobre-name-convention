"""Application use cases for versioned document Review state."""

from dataclasses import replace
from datetime import UTC, datetime
from typing import Never
from uuid import UUID, uuid4

from docmind_api.application.document_review.commands import (
    DecideDocumentApprovalCommand,
    SaveDocumentReviewCommand,
)
from docmind_api.application.document_review.errors import (
    DocumentApprovalDecisionRejectedError,
    DocumentReviewNotInitializedError,
    DocumentReviewValidationError,
    DocumentReviewVersionConflictError,
)
from docmind_api.application.document_review.ports import (
    DocumentApprovalCompletionPort,
    DocumentApprovalSettingsRepository,
    DocumentApprovalWorkflowRepository,
    DocumentReviewPipelineSource,
    DocumentReviewProvider,
    DocumentReviewRepository,
)
from docmind_api.application.document_review.read_models import (
    DocumentReviewApproval,
    DocumentReviewApprovalHistoryItem,
    DocumentReviewApprovalStep,
    DocumentReviewAttribute,
    DocumentReviewAttributeKind,
    DocumentReviewAttributeStatus,
    DocumentReviewDataSource,
    DocumentReviewHistoryPage,
    DocumentReviewProcessingStatus,
    DocumentReviewResult,
    DocumentReviewValidation,
    DocumentReviewValueSource,
)
from docmind_api.application.documents.errors import (
    DocumentArchivedError,
    DocumentNotFoundError,
)
from docmind_api.application.documents.ports import DocumentRegistryRepository
from docmind_api.domain.documents.approval import (
    DocumentApprovalDecision,
    DocumentApprovalStep,
    DocumentApprovalWorkflow,
    DocumentApprovalWorkflowStatus,
)
from docmind_api.domain.documents.approval_settings import (
    default_document_approval_settings,
)
from docmind_api.domain.documents.models import DocumentStatus


class DocumentReviewService:
    """Read, initialize, and atomically version one document Review."""

    def __init__(
        self,
        *,
        provider: DocumentReviewProvider,
        repository: DocumentReviewRepository | None = None,
        pipeline_source: DocumentReviewPipelineSource | None = None,
        approval_repository: DocumentApprovalWorkflowRepository | None = None,
        approval_settings_repository: DocumentApprovalSettingsRepository | None = None,
        approval_completion: DocumentApprovalCompletionPort | None = None,
        document_repository: DocumentRegistryRepository | None = None,
    ) -> None:
        self._provider = provider
        self._repository = repository
        self._pipeline_source = pipeline_source
        self._approval_repository = approval_repository
        self._approval_settings_repository = approval_settings_repository
        self._approval_completion = approval_completion
        self._document_repository = document_repository

    async def get_review(
        self,
        document_id: UUID,
        *,
        actor_id: str | None = None,
    ) -> DocumentReviewResult:
        """Return current Review, repairing it from a committed pipeline result when needed."""

        if self._repository is not None:
            current = await self._repository.get_current(document_id)
            if current is not None:
                current = await self._hydrate_pipeline_sources(current)
                return await self._with_approval(current, actor_id=actor_id)
            if self._pipeline_source is not None:
                pipeline_result = await self._pipeline_source.get_first_eligible(document_id)
                if pipeline_result is not None:
                    await self.initialize_from_pipeline(pipeline_result)
                    current = await self._repository.get_current(document_id)
                    if current is not None:
                        return await self._with_approval(current, actor_id=actor_id)
                    return await self._with_approval(
                        replace(
                            pipeline_result,
                            processing_status=DocumentReviewProcessingStatus.PENDING,
                            attributes_available=False,
                            unavailable_reason_code="REVIEW_INITIALIZATION_PENDING",
                            attributes=(),
                        ),
                        actor_id=actor_id,
                    )
        return await self._with_approval(
            await self._provider.get_review(document_id),
            actor_id=actor_id,
        )

    async def _hydrate_pipeline_sources(
        self,
        current: DocumentReviewResult,
    ) -> DocumentReviewResult:
        pipeline_source = self._pipeline_source
        run_id = current.source_pipeline_run_id
        if pipeline_source is None or run_id is None:
            return current
        if not any(
            not field.sources
            and field.value_source is DocumentReviewValueSource.PIPELINE
            and not field.manually_edited
            for field in current.attributes
        ):
            return current

        pipeline_result = await pipeline_source.get_for_run(current.document_id, run_id)
        if pipeline_result is None:
            return current
        sources_by_id = {
            field.id: field.sources for field in pipeline_result.attributes if field.sources
        }
        if not sources_by_id:
            return current
        return replace(
            current,
            attributes=tuple(
                replace(field, sources=sources_by_id[field.id])
                if (
                    not field.sources
                    and field.value_source is DocumentReviewValueSource.PIPELINE
                    and not field.manually_edited
                    and field.id in sources_by_id
                )
                else field
                for field in current.attributes
            ),
        )

    async def decide_approval(
        self,
        command: DecideDocumentApprovalCommand,
    ) -> DocumentReviewApproval:
        """Record an approval or rejection and return the new workflow state."""

        await self._ensure_document_mutable(command.document_id)
        if self._approval_repository is None:
            raise DocumentReviewNotInitializedError(document_id=command.document_id)
        if command.decision is DocumentApprovalDecision.APPROVED:
            await self._reject_approval_for_missing_required_fields(command)
        workflow = await self._approval_repository.decide(
            document_id=command.document_id,
            actor_id=command.actor_id,
            expected_review_version=command.expected_review_version,
            decision=command.decision,
            comment=_normalize_value(command.comment),
        )
        if (
            workflow.status is DocumentApprovalWorkflowStatus.APPROVED
            and self._approval_completion is not None
        ):
            await self._approval_completion.complete(
                document_id=command.document_id,
                workflow=workflow,
            )
        return _approval_projection(workflow, actor_id=command.actor_id)

    async def _reject_approval_for_missing_required_fields(
        self,
        command: DecideDocumentApprovalCommand,
    ) -> None:
        if self._repository is None:
            raise DocumentReviewNotInitializedError(document_id=command.document_id)
        current = await self._repository.get_current(command.document_id)
        if current is None or current.version is None:
            raise DocumentReviewNotInitializedError(document_id=command.document_id)
        if current.version != command.expected_review_version:
            raise DocumentApprovalDecisionRejectedError(
                code="DOCUMENT_APPROVAL_REVIEW_VERSION_CONFLICT",
                message="The document Review changed before the approval decision was recorded.",
            )
        blocking_field_ids = [
            str(field.id)
            for field in current.attributes
            if field.required and _normalize_value(field.value) is None
        ]
        if blocking_field_ids:
            raise DocumentApprovalDecisionRejectedError(
                code="DOCUMENT_APPROVAL_MISSING_REQUIRED_FIELDS",
                message="Required Review fields must have values before approval.",
                details={"blocking_field_ids": blocking_field_ids},
            )

    async def _with_approval(
        self,
        result: DocumentReviewResult,
        *,
        actor_id: str | None,
    ) -> DocumentReviewResult:
        if self._approval_repository is None:
            return replace(result, approval=None)
        workflow = await self._approval_repository.get(result.document_id)
        if workflow is None:
            return replace(result, approval=None)
        return replace(result, approval=_approval_projection(workflow, actor_id=actor_id))

    async def list_history(
        self,
        document_id: UUID,
        *,
        limit: int,
        offset: int,
    ) -> DocumentReviewHistoryPage:
        """Return immutable version summaries, newest first."""

        if self._repository is None:
            return DocumentReviewHistoryPage(items=(), limit=limit, offset=offset, has_more=False)
        current = await self._repository.get_current(document_id)
        if current is None:
            await self._provider.get_review(document_id)
            return DocumentReviewHistoryPage(items=(), limit=limit, offset=offset, has_more=False)
        items = await self._repository.list_history(
            document_id,
            limit=limit + 1,
            offset=offset,
        )
        return DocumentReviewHistoryPage(
            items=items[:limit],
            limit=limit,
            offset=offset,
            has_more=len(items) > limit,
        )

    async def save_review(self, command: SaveDocumentReviewCommand) -> DocumentReviewResult:
        """Save the complete field list as one new immutable Review version."""

        await self._ensure_document_mutable(command.document_id)
        if self._repository is None:
            raise DocumentReviewNotInitializedError(document_id=command.document_id)
        current = await self._repository.get_current(command.document_id)
        initialized = False
        if current is None:
            current, initialized = await self._initialize_from_fallback(command.document_id)
        current = await self._hydrate_pipeline_sources(current)
        effective_expected_version = command.expected_version
        if initialized and effective_expected_version is None:
            effective_expected_version = current.version
        if effective_expected_version is None or current.version != effective_expected_version:
            await self._raise_version_conflict(command=command, current=current)

        updated = _build_next_version(current=current, command=command)
        if self._approval_repository is not None:
            if updated.version is None:
                raise RuntimeError("Next Review version must be initialized.")
            await self._approval_repository.reset_for_review_version(
                document_id=command.document_id,
                review_version=updated.version,
            )
        saved = await self._repository.save_next(
            result=updated,
            expected_version=effective_expected_version,
        )
        if saved:
            return await self._with_approval(updated, actor_id=command.actor_id)

        latest = await self._repository.get_current(command.document_id)
        if latest is None:
            raise DocumentReviewNotInitializedError(document_id=command.document_id)
        await self._raise_version_conflict(command=command, current=latest)
        raise RuntimeError("Version conflict handler must raise.")

    async def _ensure_document_mutable(self, document_id: UUID) -> None:
        if self._document_repository is None:
            return
        document = await self._document_repository.get_by_id_for_update(document_id)
        if document is None:
            raise DocumentNotFoundError(document_id=document_id)
        if document.status is DocumentStatus.APPROVED:
            raise DocumentArchivedError(document_id=document_id)

    async def initialize_from_pipeline(self, result: DocumentReviewResult) -> bool:
        """Create Review version 1 once from a completed pipeline projection."""

        if self._repository is None or result.data_source is not DocumentReviewDataSource.PIPELINE:
            return False
        if not result.attributes_available or result.source_pipeline_run_id is None:
            return False
        timestamp = datetime.now(tz=UTC)
        initial = _initial_version(result, timestamp=timestamp)
        initialized = await self._repository.initialize(initial)
        if initialized and self._approval_repository is not None:
            await self._initialize_approval(result.document_id)
        return initialized

    async def initialize_from_first_pipeline_result(self, document_id: UUID) -> bool:
        """Initialize Review from the oldest eligible pipeline result exactly once."""

        if self._repository is None or self._pipeline_source is None:
            return False
        if await self._repository.get_current(document_id) is not None:
            return False
        result = await self._pipeline_source.get_first_eligible(document_id)
        if result is None:
            return False
        return await self.initialize_from_pipeline(result)

    async def reset_for_document_type_change(
        self,
        document_id: UUID,
        pipeline_run_id: UUID,
    ) -> bool:
        """Hide stale Review data until the replacement pipeline run completes."""

        if self._repository is None:
            return False
        current = await self._repository.get_current(document_id)
        if current is None or current.version is None:
            return False
        replacement = replace(
            current,
            data_source=DocumentReviewDataSource.PIPELINE,
            processing_status=DocumentReviewProcessingStatus.PENDING,
            attributes_available=False,
            unavailable_reason_code="REVIEW_REPROCESSING_PENDING",
            attributes=(),
            review_id=current.review_id,
            version=current.version + 1,
            source_pipeline_run_id=pipeline_run_id,
            quality_score=None,
            validations=(),
            updated_at=datetime.now(tz=UTC),
            updated_by_actor_id=None,
            is_reprocessing=True,
        )
        if replacement.version is None:
            raise RuntimeError("Replacement Review version must be initialized.")
        if self._approval_repository is not None:
            await self._approval_repository.reset_for_review_version(
                document_id=document_id,
                review_version=replacement.version,
            )
        return await self._repository.save_next(
            result=replacement,
            expected_version=current.version,
        )

    async def replace_reprocessing_review_from_pipeline_run(
        self,
        document_id: UUID,
        pipeline_run_id: UUID,
    ) -> bool:
        """Replace a type-change placeholder with its exact pipeline result."""

        if self._repository is None or self._pipeline_source is None:
            return False
        if await self._document_is_archived_for_update(document_id):
            return False
        current = await self._repository.get_current(document_id)
        if (
            current is None
            or (current.is_reprocessing and current.source_pipeline_run_id != pipeline_run_id)
            or current.version is None
        ):
            return False
        pipeline_result = await self._pipeline_source.get_for_run(document_id, pipeline_run_id)
        if pipeline_result is None:
            return False
        replacement = replace(
            _initial_version(pipeline_result, timestamp=datetime.now(tz=UTC)),
            review_id=current.review_id,
            version=current.version + 1,
            is_reprocessing=False,
        )
        if replacement.version is None:
            raise RuntimeError("Replacement Review version must be initialized.")
        if self._approval_repository is not None:
            await self._approval_repository.reset_for_review_version(
                document_id=document_id,
                review_version=replacement.version,
            )
        return await self._repository.save_next(
            result=replacement,
            expected_version=current.version,
        )

    async def _document_is_archived_for_update(self, document_id: UUID) -> bool:
        if self._document_repository is None:
            return False
        document = await self._document_repository.get_by_id_for_update(document_id)
        return document is not None and document.status is DocumentStatus.APPROVED

    async def _initialize_from_fallback(
        self,
        document_id: UUID,
    ) -> tuple[DocumentReviewResult, bool]:
        repository = self._repository
        if repository is None:
            raise DocumentReviewNotInitializedError(document_id=document_id)
        if self._pipeline_source is not None:
            pipeline_result = await self._pipeline_source.get_first_eligible(document_id)
            if pipeline_result is not None:
                raise DocumentReviewNotInitializedError(document_id=document_id)
        projection = await self._provider.get_review(document_id)
        if not projection.attributes_available:
            raise DocumentReviewNotInitializedError(document_id=document_id)
        timestamp = datetime.now(tz=UTC)
        initial = _initial_version(projection, timestamp=timestamp)
        initialized = await repository.initialize(initial)
        if initialized and self._approval_repository is not None:
            await self._initialize_approval(document_id)
        current = await repository.get_current(document_id)
        if current is None:
            raise DocumentReviewNotInitializedError(document_id=document_id)
        return current, initialized

    async def _initialize_approval(self, document_id: UUID) -> None:
        approval_repository = self._approval_repository
        if approval_repository is None:
            return
        settings = (
            await self._approval_settings_repository.get()
            if self._approval_settings_repository is not None
            else None
        )
        required_approvals = (settings or default_document_approval_settings()).required_approvals
        await approval_repository.initialize(
            document_id,
            required_approvals=required_approvals,
        )

    async def _raise_version_conflict(
        self,
        *,
        command: SaveDocumentReviewCommand,
        current: DocumentReviewResult,
    ) -> Never:
        if self._repository is None:
            raise DocumentReviewNotInitializedError(document_id=command.document_id)
        base = (
            await self._repository.get_version(command.document_id, command.expected_version)
            if command.expected_version is not None
            else None
        )
        server_changed = _changed_field_ids(base=base, current=current)
        client_changed = _client_changed_field_ids(base=base, command=command)
        conflicting = server_changed.intersection(client_changed)
        raise DocumentReviewVersionConflictError(
            details={
                "document_id": str(command.document_id),
                "expected_version": command.expected_version,
                "current_version": current.version,
                "server_changed_field_ids": _sorted_ids(server_changed),
                "client_changed_field_ids": _sorted_ids(client_changed),
                "conflicting_field_ids": _sorted_ids(conflicting),
            },
        )


def _initial_version(result: DocumentReviewResult, *, timestamp: datetime) -> DocumentReviewResult:
    attributes = tuple(
        replace(
            field,
            value_source=(
                DocumentReviewValueSource.MOCK
                if result.data_source is DocumentReviewDataSource.MOCK
                else DocumentReviewValueSource.PIPELINE
            ),
        )
        for field in result.attributes
    )
    validations, score = _calculate_review_state(attributes)
    return replace(
        result,
        review_id=uuid4(),
        version=1,
        quality_score=score,
        validations=validations,
        created_at=timestamp,
        updated_at=timestamp,
        updated_by_actor_id=None,
        attributes=attributes,
    )


def _build_next_version(
    *,
    current: DocumentReviewResult,
    command: SaveDocumentReviewCommand,
) -> DocumentReviewResult:
    if current.review_id is None or current.version is None or current.created_at is None:
        raise DocumentReviewNotInitializedError(document_id=command.document_id)
    existing = {field.id: field for field in current.attributes}
    submitted_ids = [field.id for field in command.fields if field.id is not None]
    if len(submitted_ids) != len(set(submitted_ids)):
        raise DocumentReviewValidationError(message="Review field ids must be unique.")

    updated_fields: list[DocumentReviewAttribute] = []
    next_order = max((field.display_order for field in current.attributes), default=0)
    for submitted in command.fields:
        value = _normalize_value(submitted.value)
        if submitted.id is None:
            label = submitted.label.strip()
            if not label:
                raise DocumentReviewValidationError(message="Manual field label cannot be empty.")
            next_order += 10
            updated_fields.append(
                DocumentReviewAttribute(
                    id=uuid4(),
                    kind=DocumentReviewAttributeKind.MANUAL,
                    attribute_id=None,
                    attribute_external_id=None,
                    label=label,
                    data_type=submitted.data_type,
                    required=False,
                    display_order=next_order,
                    value=value,
                    display_value=value,
                    confidence=None,
                    status=_status_for_value(value),
                    requires_review=False,
                    review_reason_codes=(),
                    sources=(),
                    value_source=DocumentReviewValueSource.MANUAL,
                    manually_edited=True,
                ),
            )
            continue

        previous = existing.get(submitted.id)
        if previous is None:
            raise DocumentReviewValidationError(
                message="Review contains an unknown or deleted field id.",
                details={"field_id": str(submitted.id)},
            )
        if previous.kind is DocumentReviewAttributeKind.CONFIGURED and (
            submitted.label.strip() != previous.label or submitted.data_type != previous.data_type
        ):
            raise DocumentReviewValidationError(
                message="Configured field label and data type cannot be changed.",
                details={"field_id": str(previous.id)},
            )

        manually_changed = value != previous.value or (
            previous.kind is DocumentReviewAttributeKind.MANUAL
            and submitted.label.strip() != previous.label
        )
        is_manual = previous.manually_edited or manually_changed
        updated_fields.append(
            replace(
                previous,
                label=(
                    submitted.label.strip()
                    if previous.kind is DocumentReviewAttributeKind.MANUAL
                    else previous.label
                ),
                data_type=(
                    submitted.data_type
                    if previous.kind is DocumentReviewAttributeKind.MANUAL
                    else previous.data_type
                ),
                value=value,
                display_value=value,
                confidence=None if is_manual else previous.confidence,
                sources=previous.sources,
                status=_status_for_value(value),
                value_source=(
                    DocumentReviewValueSource.MANUAL if is_manual else previous.value_source
                ),
                manually_edited=is_manual,
                review_reason_codes=(
                    ("MISSING_REQUIRED_VALUE",) if previous.required and value is None else ()
                ),
                requires_review=previous.required and value is None,
            ),
        )

    attributes = tuple(updated_fields)
    validations, score = _calculate_review_state(attributes)
    timestamp = datetime.now(tz=UTC)
    return replace(
        current,
        version=current.version + 1,
        data_source=DocumentReviewDataSource.MANUAL,
        source_pipeline_run_id=None,
        attributes=attributes,
        quality_score=score,
        validations=validations,
        updated_at=timestamp,
        updated_by_actor_id=command.actor_id,
    )


def _calculate_review_state(
    fields: tuple[DocumentReviewAttribute, ...],
) -> tuple[tuple[DocumentReviewValidation, ...], float]:
    configured = tuple(
        field for field in fields if field.kind is DocumentReviewAttributeKind.CONFIGURED
    )
    missing_required = tuple(
        field for field in configured if field.required and field.value is None
    )
    validations = tuple(
        DocumentReviewValidation(
            code="MISSING_REQUIRED_VALUE",
            severity="error",
            field_id=field.id,
            message=f"Required field '{field.label}' has no value.",
        )
        for field in missing_required
    )
    if not configured:
        return validations, 1.0
    present_count = sum(field.value is not None for field in configured)
    return validations, round(present_count / len(configured), 4)


def _changed_field_ids(
    *,
    base: DocumentReviewResult | None,
    current: DocumentReviewResult,
) -> set[UUID]:
    if base is None:
        return {field.id for field in current.attributes}
    base_fields = {field.id: _field_state(field) for field in base.attributes}
    current_fields = {field.id: _field_state(field) for field in current.attributes}
    return {
        field_id
        for field_id in set(base_fields).union(current_fields)
        if base_fields.get(field_id) != current_fields.get(field_id)
    }


def _client_changed_field_ids(
    *,
    base: DocumentReviewResult | None,
    command: SaveDocumentReviewCommand,
) -> set[UUID]:
    if base is None:
        return {field.id for field in command.fields if field.id is not None}
    base_fields = {field.id: _field_state(field) for field in base.attributes}
    submitted = {
        field.id: (field.label.strip(), field.data_type.value, _normalize_value(field.value))
        for field in command.fields
        if field.id is not None
    }
    return {
        field_id
        for field_id in set(base_fields).union(submitted)
        if (
            (base_fields[field_id][0], base_fields[field_id][1], base_fields[field_id][2])
            if field_id in base_fields
            else None
        )
        != submitted.get(field_id)
    }


def _field_state(field: DocumentReviewAttribute) -> tuple[str, str, str | None]:
    return (field.label, field.data_type.value, field.value)


def _sorted_ids(values: set[UUID]) -> list[str]:
    return [str(value) for value in sorted(values, key=str)]


def _normalize_value(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _status_for_value(value: str | None) -> DocumentReviewAttributeStatus:
    return (
        DocumentReviewAttributeStatus.MISSING
        if value is None
        else DocumentReviewAttributeStatus.PRESENT
    )


def _approval_projection(
    workflow: DocumentApprovalWorkflow,
    *,
    actor_id: str | None,
) -> DocumentReviewApproval:
    return DocumentReviewApproval(
        run_number=workflow.run_number,
        status=workflow.status,
        is_current_actor_active_reviewer=(
            actor_id is not None and workflow.is_actor_active(actor_id)
        ),
        steps=tuple(_approval_step_projection(step) for step in workflow.steps),
        history=tuple(
            DocumentReviewApprovalHistoryItem(
                run_number=item.run_number,
                step_number=item.step_number,
                decision=item.decision,
                actor_id=item.actor_id,
                comment=item.comment,
                decided_at=item.decided_at,
                actor_display_name=item.actor_display_name,
            )
            for item in workflow.history
        ),
    )


def _approval_step_projection(step: DocumentApprovalStep) -> DocumentReviewApprovalStep:
    return DocumentReviewApprovalStep(
        number=step.number,
        status=step.status,
        reviewer_actor_id=step.reviewer_actor_id,
        decided_at=step.decided_at,
        comment=step.comment,
        reviewer_display_name=step.reviewer_display_name,
    )
