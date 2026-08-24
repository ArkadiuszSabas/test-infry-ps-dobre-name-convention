"""Temporary document review providers used before pipeline result mapping exists."""

from dataclasses import dataclass
from uuid import NAMESPACE_URL, UUID, uuid5

from docmind_api.application.attribute_requirements.ports import (
    AttributeRequirementRepository,
)
from docmind_api.application.attributes.ports import (
    AttributeCategoryRepository,
    AttributeDefinitionRepository,
)
from docmind_api.application.document_review.read_models import (
    DocumentReviewAttribute,
    DocumentReviewAttributeKind,
    DocumentReviewAttributeStatus,
    DocumentReviewDataSource,
    DocumentReviewProcessingStatus,
    DocumentReviewResult,
    DocumentReviewValueSource,
)
from docmind_api.application.documents.errors import DocumentNotFoundError
from docmind_api.application.documents.ports import DocumentRegistryRepository
from docmind_api.domain.attribute_requirements.models import (
    DocumentTypeAttributeRequirement,
)
from docmind_api.domain.attributes.models import AttributeDefinition, attribute_category_is_metadata

_MOCK_VALUE = "TBD: Not implemented yet"


class MockDocumentReviewProvider:
    """Build configured rows with deterministic fake extraction results."""

    def __init__(
        self,
        *,
        document_repository: DocumentRegistryRepository,
        requirement_repository: AttributeRequirementRepository,
        attribute_repository: AttributeDefinitionRepository,
        attribute_category_repository: AttributeCategoryRepository,
    ) -> None:
        self._document_repository = document_repository
        self._requirement_repository = requirement_repository
        self._attribute_repository = attribute_repository
        self._attribute_category_repository = attribute_category_repository

    async def get_review(self, document_id: UUID) -> DocumentReviewResult:
        """Read configured attributes and add stable placeholder extraction values."""

        document = await self._document_repository.get_by_id(document_id)
        if document is None:
            raise DocumentNotFoundError(document_id=document_id)

        requirements = await self._requirement_repository.list_for_document_type(
            document.document_type_id,
        )
        requirements_by_attribute_id = {
            requirement.attribute_definition_id: requirement for requirement in requirements
        }
        configured_attributes: list[AttributeDefinition] = []
        for attribute in await self._attribute_repository.list():
            if UUID(str(attribute.id)) not in requirements_by_attribute_id:
                continue
            if attribute.category_id is not None:
                category = await self._attribute_category_repository.get_by_id(
                    attribute.category_id
                )
                if (
                    category is not None
                    and category.is_active
                    and attribute_category_is_metadata(category)
                ):
                    continue
            configured_attributes.append(attribute)

        return DocumentReviewResult(
            schema_version=2,
            document_id=document_id,
            data_source=DocumentReviewDataSource.MOCK,
            processing_status=DocumentReviewProcessingStatus.COMPLETED,
            attributes_available=True,
            unavailable_reason_code=None,
            attributes=tuple(
                _mock_attribute(
                    document_id=document_id,
                    display_order=(index + 1) * 10,
                    attribute=attribute,
                    requirement=requirements_by_attribute_id[UUID(str(attribute.id))],
                    state_index=index,
                )
                for index, attribute in enumerate(configured_attributes)
            ),
        )


class UnavailableDocumentReviewProvider:
    """Fail closed when mock review data is disabled for the environment."""

    def __init__(self, *, document_repository: DocumentRegistryRepository) -> None:
        self._document_repository = document_repository

    async def get_review(self, document_id: UUID) -> DocumentReviewResult:
        """Return an explicit unavailable state instead of fake production data."""

        document = await self._document_repository.get_by_id(document_id)
        if document is None:
            raise DocumentNotFoundError(document_id=document_id)

        return DocumentReviewResult(
            schema_version=2,
            document_id=document_id,
            data_source=DocumentReviewDataSource.UNAVAILABLE,
            processing_status=DocumentReviewProcessingStatus.NOT_AVAILABLE,
            attributes_available=False,
            unavailable_reason_code="REVIEW_DATA_NOT_AVAILABLE",
            attributes=(),
        )


@dataclass(frozen=True, slots=True)
class _MockState:
    status: DocumentReviewAttributeStatus
    confidence: float | None
    value: str | None
    requires_review: bool
    review_reason_codes: tuple[str, ...]


def _mock_attribute(
    *,
    document_id: UUID,
    display_order: int,
    attribute: AttributeDefinition,
    requirement: DocumentTypeAttributeRequirement,
    state_index: int,
) -> DocumentReviewAttribute:
    state = _mock_state(state_index=state_index, required=requirement.required)
    attribute_id = UUID(str(attribute.id))
    return DocumentReviewAttribute(
        id=uuid5(
            NAMESPACE_URL,
            f"docmind:mock-review-result:{document_id}:{attribute_id}",
        ),
        kind=DocumentReviewAttributeKind.CONFIGURED,
        attribute_id=attribute_id,
        attribute_external_id=attribute.external_id,
        label=attribute.name,
        data_type=attribute.data_type,
        required=requirement.required,
        display_order=display_order,
        value=state.value,
        display_value=state.value,
        confidence=state.confidence,
        status=state.status,
        requires_review=state.requires_review,
        review_reason_codes=state.review_reason_codes,
        sources=(),
        value_source=DocumentReviewValueSource.MOCK,
        manually_edited=False,
    )


def _mock_state(*, state_index: int, required: bool) -> _MockState:
    variant = state_index % 4
    if variant == 0:
        return _MockState(
            status=DocumentReviewAttributeStatus.PRESENT,
            confidence=0.96,
            value=_MOCK_VALUE,
            requires_review=False,
            review_reason_codes=(),
        )
    if variant == 1:
        return _MockState(
            status=DocumentReviewAttributeStatus.MISSING,
            confidence=None,
            value=None,
            requires_review=required,
            review_reason_codes=("MISSING_REQUIRED_VALUE",) if required else (),
        )
    if variant == 2:
        return _MockState(
            status=DocumentReviewAttributeStatus.UNCERTAIN,
            confidence=0.41,
            value=_MOCK_VALUE,
            requires_review=True,
            review_reason_codes=("LOW_CONFIDENCE",),
        )
    return _MockState(
        status=DocumentReviewAttributeStatus.CONFLICTING,
        confidence=0.52,
        value=_MOCK_VALUE,
        requires_review=True,
        review_reason_codes=("CONFLICTING_VALUES",),
    )
