"""Attribute definition catalog application use cases."""

from dataclasses import dataclass, field
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from docmind_api.application.attributes.deactivation_guards import (
    raise_for_active_deactivation_usage,
)
from docmind_api.application.attributes.errors import (
    AttributeDefinitionAlreadyExistsError,
    AttributeDefinitionInUseError,
    AttributeDefinitionNotFoundError,
    AttributeDefinitionValidationError,
)
from docmind_api.application.attributes.ports import (
    AttributeCategoryCount,
    AttributeCategoryRepository,
    AttributeDefinitionIdFactory,
    AttributeDefinitionRepository,
    AttributeDefinitionUsageRepository,
    AttributeDictionaryReferenceRepository,
    Clock,
)
from docmind_api.domain.attributes.models import (
    ATTRIBUTE_CATEGORY_DEFAULT_EXTERNAL_ID,
    AttributeCategory,
    AttributeConstraints,
    AttributeDataType,
    AttributeDefinition,
    AttributeSource,
    AttributeStatus,
    AttributeValueSource,
    normalize_attribute_external_id,
)


@dataclass(frozen=True, slots=True)
class CreateAttributeDefinitionCommand:
    name: str
    source: AttributeSource
    external_id: str | None = None
    category_id: UUID | None = None
    data_type: AttributeDataType = AttributeDataType.STRING
    constraints: AttributeConstraints = field(default_factory=AttributeConstraints)
    allowed_values: tuple[str, ...] = field(default_factory=tuple)
    value_source: AttributeValueSource = AttributeValueSource.FREE_TEXT
    dictionary_id: UUID | None = None
    comment: str | None = None
    llm_context: str | None = None
    id: str | None = None


@dataclass(frozen=True, slots=True)
class ListAttributeDefinitionsQuery:
    category: str | None = None


class PreserveAttributeField:
    __slots__ = ()


PRESERVE_ATTRIBUTE_FIELD = PreserveAttributeField()
type AttributeNameUpdate = str | PreserveAttributeField
type AttributeExternalIdUpdate = str | None | PreserveAttributeField
type AttributeCategoryIdUpdate = UUID | None | PreserveAttributeField
type AttributeDataTypeUpdate = AttributeDataType | PreserveAttributeField
type AttributeConstraintsUpdate = AttributeConstraints | PreserveAttributeField
type AttributeAllowedValuesUpdate = tuple[str, ...] | PreserveAttributeField
type AttributeValueSourceUpdate = AttributeValueSource | PreserveAttributeField
type AttributeDictionaryIdUpdate = UUID | None | PreserveAttributeField
type AttributeSourceUpdate = AttributeSource | PreserveAttributeField
type AttributeCommentUpdate = str | None | PreserveAttributeField
type AttributeLlmContextUpdate = str | None | PreserveAttributeField


@dataclass(frozen=True, slots=True)
class UpdateAttributeDefinitionCommand:
    attribute_id: UUID | str
    external_id: AttributeExternalIdUpdate = PRESERVE_ATTRIBUTE_FIELD
    name: AttributeNameUpdate = PRESERVE_ATTRIBUTE_FIELD
    category_id: AttributeCategoryIdUpdate = PRESERVE_ATTRIBUTE_FIELD
    data_type: AttributeDataTypeUpdate = PRESERVE_ATTRIBUTE_FIELD
    constraints: AttributeConstraintsUpdate = PRESERVE_ATTRIBUTE_FIELD
    allowed_values: AttributeAllowedValuesUpdate = PRESERVE_ATTRIBUTE_FIELD
    value_source: AttributeValueSourceUpdate = PRESERVE_ATTRIBUTE_FIELD
    dictionary_id: AttributeDictionaryIdUpdate = PRESERVE_ATTRIBUTE_FIELD
    source: AttributeSourceUpdate = PRESERVE_ATTRIBUTE_FIELD
    comment: AttributeCommentUpdate = PRESERVE_ATTRIBUTE_FIELD
    llm_context: AttributeLlmContextUpdate = PRESERVE_ATTRIBUTE_FIELD


@dataclass(frozen=True, slots=True)
class DeactivateAttributeDefinitionCommand:
    attribute_id: UUID | str


@dataclass(frozen=True, slots=True)
class DeleteAttributeDefinitionCommand:
    attribute_id: UUID | str


@dataclass(frozen=True, slots=True)
class DeleteAttributeDefinitionResult:
    attribute_id: UUID
    deleted: bool


@dataclass(frozen=True, slots=True)
class AttributeDefinitionList:
    attributes: tuple[AttributeDefinition, ...]
    category_counts: tuple[AttributeCategoryCount, ...]


class AttributeDefinitionCatalogService:
    """Application service for attribute definition catalog workflows."""

    def __init__(
        self,
        *,
        repository: AttributeDefinitionRepository,
        usage_repository: AttributeDefinitionUsageRepository,
        clock: Clock,
        id_factory: AttributeDefinitionIdFactory | None = None,
        category_repository: AttributeCategoryRepository | None = None,
        dictionary_reference_repository: AttributeDictionaryReferenceRepository | None = None,
    ) -> None:
        self._repository = repository
        self._usage_repository = usage_repository
        self._id_factory = id_factory
        self._clock = clock
        self._category_repository = category_repository
        self._dictionary_reference_repository = dictionary_reference_repository

    async def create_attribute_definition(
        self,
        command: CreateAttributeDefinitionCommand,
    ) -> AttributeDefinition:
        timestamp = self._clock.now()
        try:
            external_id = _create_command_external_id(command)
            category = await self._category_from_id_or_default(command.category_id)
            attribute = AttributeDefinition(
                id=(
                    self._id_factory.new_id()
                    if self._id_factory is not None
                    else _generated_attribute_definition_id(external_id)
                ),
                external_id=external_id,
                name=command.name,
                category=category.label,
                category_id=category.id,
                data_type=command.data_type,
                constraints=command.constraints,
                allowed_values=command.allowed_values,
                value_source=command.value_source,
                dictionary_id=command.dictionary_id,
                source=command.source,
                comment=command.comment,
                llm_context=command.llm_context,
                status=AttributeStatus.ACTIVE,
                created_at=timestamp,
                updated_at=timestamp,
            )
        except ValueError as error:
            raise AttributeDefinitionValidationError(message=str(error)) from error

        await self._validate_dictionary_binding(attribute)
        if (
            attribute.external_id is not None
            and await self._repository.get_by_external_id(attribute.external_id) is not None
        ):
            raise AttributeDefinitionAlreadyExistsError(external_id=attribute.external_id)

        created = await self._repository.add(attribute)
        if not created:
            raise AttributeDefinitionAlreadyExistsError(external_id=attribute.external_id)

        return attribute

    async def update_attribute_definition(
        self,
        command: UpdateAttributeDefinitionCommand,
    ) -> AttributeDefinition:
        attribute_reference = _validated_attribute_id(command.attribute_id)
        existing_attribute = await self._repository.get_by_id(attribute_reference)
        if existing_attribute is None:
            raise AttributeDefinitionNotFoundError(attribute_id=attribute_reference)

        try:
            category, category_id = await self._category_update_from_command(
                command=command,
                existing_attribute=existing_attribute,
            )
            updated_attribute = existing_attribute.update_business_fields(
                external_id=_resolve_update(
                    command.external_id,
                    existing_attribute.external_id,
                ),
                name=_resolve_update(command.name, existing_attribute.name),
                category=category,
                category_id=category_id,
                data_type=_resolve_update(command.data_type, existing_attribute.data_type),
                constraints=_resolve_update(
                    command.constraints,
                    existing_attribute.constraints,
                ),
                allowed_values=_resolve_update(
                    command.allowed_values,
                    existing_attribute.allowed_values,
                ),
                value_source=_resolve_update(
                    command.value_source,
                    existing_attribute.value_source,
                ),
                dictionary_id=_resolve_update(
                    command.dictionary_id,
                    existing_attribute.dictionary_id,
                ),
                source=_resolve_update(command.source, existing_attribute.source),
                comment=_resolve_update(command.comment, existing_attribute.comment),
                updated_at=self._clock.now(),
                llm_context=_resolve_update(
                    command.llm_context,
                    existing_attribute.llm_context,
                ),
            )
        except ValueError as error:
            raise AttributeDefinitionValidationError(message=str(error)) from error

        await self._validate_dictionary_binding(updated_attribute)
        if updated_attribute.external_id != existing_attribute.external_id:
            duplicate = (
                await self._repository.get_by_external_id(updated_attribute.external_id)
                if updated_attribute.external_id is not None
                else None
            )
            if duplicate is not None and duplicate.id != existing_attribute.id:
                raise AttributeDefinitionAlreadyExistsError(
                    external_id=updated_attribute.external_id,
                )
        updated = await self._repository.update_business_fields(updated_attribute)
        if not updated:
            raise AttributeDefinitionNotFoundError(attribute_id=existing_attribute.id)

        return updated_attribute

    async def deactivate_attribute_definition(
        self,
        command: DeactivateAttributeDefinitionCommand,
    ) -> AttributeDefinition:
        attribute_reference = _validated_attribute_id(command.attribute_id)
        attribute = await self._repository.get_by_id(attribute_reference)
        if attribute is None:
            raise AttributeDefinitionNotFoundError(attribute_id=attribute_reference)

        attribute_id = UUID(str(attribute.id))
        usage = await self._usage_repository.get_usage(attribute_id)
        raise_for_active_deactivation_usage(attribute_id=attribute_id, usage=usage)
        deactivated_attribute = attribute.deactivate(updated_at=self._clock.now())
        updated = await self._repository.update_status(deactivated_attribute)
        if not updated:
            raise AttributeDefinitionNotFoundError(attribute_id=attribute.id)

        return deactivated_attribute

    async def delete_attribute_definition(
        self,
        command: DeleteAttributeDefinitionCommand,
    ) -> DeleteAttributeDefinitionResult:
        attribute_reference = _validated_attribute_id(command.attribute_id)
        attribute = await self._repository.get_by_id(attribute_reference)
        if attribute is None:
            raise AttributeDefinitionNotFoundError(attribute_id=attribute_reference)

        attribute_id = UUID(str(attribute.id))
        usage = await self._usage_repository.get_usage(attribute_id)
        if usage.has_blocking_dependencies:
            raise AttributeDefinitionInUseError(attribute_id=attribute_id, usage=usage)

        deleted = await self._repository.delete_by_id(attribute_id)
        if not deleted:
            raise AttributeDefinitionNotFoundError(attribute_id=attribute_id)

        return DeleteAttributeDefinitionResult(attribute_id=attribute_id, deleted=True)

    async def list_attribute_definitions(
        self,
        query: ListAttributeDefinitionsQuery,
    ) -> AttributeDefinitionList:
        category = _normalize_category_filter(query.category)
        attributes = await self._repository.list(category=category)
        category_counts = await self._repository.count_by_category()
        if category is not None and all(
            category_count.category != category for category_count in category_counts
        ):
            category_counts = (
                *category_counts,
                AttributeCategoryCount(category=category, count=0),
            )

        return AttributeDefinitionList(
            attributes=attributes,
            category_counts=tuple(
                sorted(category_counts, key=lambda category_count: category_count.category),
            ),
        )

    async def _validate_dictionary_binding(self, attribute: AttributeDefinition) -> None:
        if attribute.value_source != AttributeValueSource.DICTIONARY:
            return
        if attribute.dictionary_id is None:
            raise AttributeDefinitionValidationError(
                message="Dictionary value source requires dictionary_id.",
            )
        if self._dictionary_reference_repository is None:
            raise AttributeDefinitionValidationError(
                message="Dictionary binding validation is unavailable.",
            )
        dictionary = await self._dictionary_reference_repository.get_dictionary_by_id(
            attribute.dictionary_id,
        )
        if dictionary is None:
            raise AttributeDefinitionValidationError(
                message="Dictionary-bound attribute references an unknown dictionary.",
                details={"dictionary_id": str(attribute.dictionary_id)},
            )
        if not dictionary.is_active:
            raise AttributeDefinitionValidationError(
                message="Dictionary-bound attribute references an inactive dictionary.",
                details={"dictionary_id": str(attribute.dictionary_id)},
            )

    async def _category_update_from_command(
        self,
        *,
        command: UpdateAttributeDefinitionCommand,
        existing_attribute: AttributeDefinition,
    ) -> tuple[str, UUID | None]:
        if isinstance(command.category_id, PreserveAttributeField):
            if existing_attribute.category_id is None:
                if existing_attribute.category is not None:
                    return existing_attribute.category, None
                category = await self._category_from_id_or_default(None)
                return category.label, UUID(str(category.id))
            category = await self._category_from_id_or_default(
                UUID(str(existing_attribute.category_id)),
            )
            return category.label, UUID(str(category.id))

        category = await self._category_from_id_or_default(command.category_id)
        return category.label, UUID(str(category.id))

    async def _category_from_id_or_default(
        self,
        category_id: UUID | None,
    ) -> AttributeCategory:
        if self._category_repository is None:
            raise AttributeDefinitionValidationError(
                message="Attribute category catalog is unavailable.",
            )
        category = (
            await self._category_repository.get_by_id(category_id)
            if category_id is not None
            else await self._category_repository.get_by_external_id(
                ATTRIBUTE_CATEGORY_DEFAULT_EXTERNAL_ID,
            )
        )
        if category is None:
            raise AttributeDefinitionValidationError(
                message="Attribute category references an unknown system category.",
                details={"category_id": str(category_id) if category_id is not None else None},
            )
        if not category.is_active:
            raise AttributeDefinitionValidationError(
                message="Attribute category references an inactive system category.",
                details={"category_id": str(category.id)},
            )
        return category


def _normalize_category_filter(category: str | None) -> str | None:
    if category is None:
        return None

    normalized = category.strip()
    if not normalized:
        return None

    return normalized


def _validated_attribute_id(attribute_id: str | UUID) -> UUID | str:
    try:
        return UUID(str(attribute_id))
    except ValueError as error:
        try:
            return normalize_attribute_external_id(str(attribute_id))
        except ValueError as external_error:
            raise AttributeDefinitionValidationError(message=str(external_error)) from error


def _resolve_update[T](value: T | PreserveAttributeField, existing_value: T) -> T:
    if isinstance(value, PreserveAttributeField):
        return existing_value

    return value


def _create_command_external_id(command: CreateAttributeDefinitionCommand) -> str | None:
    external_id = command.external_id or command.id
    if external_id is None:
        return None

    return normalize_attribute_external_id(external_id)


def _generated_attribute_definition_id(external_id: str | None) -> UUID:
    if external_id is None:
        return uuid4()

    return uuid5(NAMESPACE_URL, f"docmind:attribute-definition:{external_id}")
