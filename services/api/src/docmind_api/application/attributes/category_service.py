"""Attribute category catalog application use cases."""

from dataclasses import dataclass, field
from enum import StrEnum
from re import sub
from unicodedata import category as unicode_category
from unicodedata import normalize
from uuid import NAMESPACE_URL, UUID, uuid5

from docmind_api.application.attributes.errors import (
    AttributeCategoryAlreadyExistsError,
    AttributeCategoryInUseError,
    AttributeCategoryNotFoundError,
    AttributeCategoryProtectedError,
    AttributeCategoryUsedByActiveAttributeError,
    AttributeCategoryValidationError,
)
from docmind_api.application.attributes.ports import (
    AttributeCategoryRepository,
    AttributeCategoryUsageRepository,
    Clock,
)
from docmind_api.domain.attributes.models import (
    ATTRIBUTE_CATEGORY_DEFAULT_EXTERNAL_ID,
    AttributeCategory,
    AttributeCategoryFlags,
    AttributeStatus,
    normalize_attribute_external_id,
)


def _empty_attribute_category_flags() -> AttributeCategoryFlags:
    return {}


@dataclass(frozen=True, slots=True)
class CreateAttributeCategoryCommand:
    label: str
    external_id: str | None = None
    flags: AttributeCategoryFlags = field(default_factory=_empty_attribute_category_flags)
    id: str | None = None


class PreserveAttributeCategoryField:
    __slots__ = ()


PRESERVE_ATTRIBUTE_CATEGORY_FIELD = PreserveAttributeCategoryField()
type AttributeCategoryLabelUpdate = str | PreserveAttributeCategoryField
type AttributeCategoryFlagsUpdate = AttributeCategoryFlags | PreserveAttributeCategoryField


@dataclass(frozen=True, slots=True)
class UpdateAttributeCategoryCommand:
    category_id: UUID | str
    label: AttributeCategoryLabelUpdate = PRESERVE_ATTRIBUTE_CATEGORY_FIELD
    flags: AttributeCategoryFlagsUpdate = PRESERVE_ATTRIBUTE_CATEGORY_FIELD


@dataclass(frozen=True, slots=True)
class DeactivateAttributeCategoryCommand:
    category_id: UUID | str


@dataclass(frozen=True, slots=True)
class DeleteAttributeCategoryCommand:
    category_id: UUID | str


@dataclass(frozen=True, slots=True)
class DeleteAttributeCategoryResult:
    category_id: UUID
    deleted: bool


class AttributeCategoryListStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ALL = "all"


@dataclass(frozen=True, slots=True)
class AttributeCategoryList:
    categories: tuple[AttributeCategory, ...]
    total_count: int
    active_count: int
    inactive_count: int
    status: AttributeCategoryListStatus

    @property
    def returned_count(self) -> int:
        return len(self.categories)


class AttributeCategoryCatalogService:
    """Application service for system attribute category workflows."""

    def __init__(
        self,
        *,
        category_repository: AttributeCategoryRepository,
        category_usage_repository: AttributeCategoryUsageRepository,
        clock: Clock,
    ) -> None:
        self._category_repository = category_repository
        self._category_usage_repository = category_usage_repository
        self._clock = clock

    async def create_attribute_category(
        self,
        command: CreateAttributeCategoryCommand,
    ) -> AttributeCategory:
        timestamp = self._clock.now()
        try:
            external_id = _create_category_external_id(command)
            category = AttributeCategory(
                id=_generated_attribute_category_id(external_id),
                external_id=external_id,
                label=command.label,
                flags=command.flags,
                status=AttributeStatus.ACTIVE,
                created_at=timestamp,
                updated_at=timestamp,
            )
        except ValueError as error:
            raise AttributeCategoryValidationError(message=str(error)) from error

        if await self._category_repository.get_by_external_id(category.external_id) is not None:
            raise AttributeCategoryAlreadyExistsError(external_id=category.external_id)

        created = await self._category_repository.add(category)
        if not created:
            raise AttributeCategoryAlreadyExistsError(external_id=category.external_id)

        return category

    async def update_attribute_category(
        self,
        command: UpdateAttributeCategoryCommand,
    ) -> AttributeCategory:
        category_reference = _validated_attribute_category_id(command.category_id)
        existing_category = await self._category_repository.get_by_id(category_reference)
        if existing_category is None:
            raise AttributeCategoryNotFoundError(category_id=category_reference)

        try:
            updated_category = existing_category.update_business_fields(
                label=_resolve_update(command.label, existing_category.label),
                flags=_resolve_update(command.flags, existing_category.flags),
                updated_at=self._clock.now(),
            )
        except ValueError as error:
            raise AttributeCategoryValidationError(message=str(error)) from error

        updated = await self._category_repository.update_business_fields(updated_category)
        if not updated:
            raise AttributeCategoryNotFoundError(category_id=existing_category.id)

        return updated_category

    async def deactivate_attribute_category(
        self,
        command: DeactivateAttributeCategoryCommand,
    ) -> AttributeCategory:
        category_reference = _validated_attribute_category_id(command.category_id)
        category = await self._category_repository.get_by_id(category_reference)
        if category is None:
            raise AttributeCategoryNotFoundError(category_id=category_reference)
        _reject_protected_category_lifecycle(category)

        category_id = UUID(str(category.id))
        usage = await self._category_usage_repository.get_usage(category_id)
        if usage.has_active_dependencies:
            raise AttributeCategoryUsedByActiveAttributeError(
                category_id=category_id,
                usage=usage,
            )

        deactivated_category = category.deactivate(updated_at=self._clock.now())
        updated = await self._category_repository.update_status(deactivated_category)
        if not updated:
            raise AttributeCategoryNotFoundError(category_id=category.id)

        return deactivated_category

    async def delete_attribute_category(
        self,
        command: DeleteAttributeCategoryCommand,
    ) -> DeleteAttributeCategoryResult:
        category_reference = _validated_attribute_category_id(command.category_id)
        category = await self._category_repository.get_by_id(category_reference)
        if category is None:
            raise AttributeCategoryNotFoundError(category_id=category_reference)
        _reject_protected_category_lifecycle(category)

        category_id = UUID(str(category.id))
        usage = await self._category_usage_repository.get_usage(category_id)
        if usage.has_blocking_dependencies:
            raise AttributeCategoryInUseError(category_id=category_id, usage=usage)

        deleted = await self._category_repository.delete_by_id(category_id)
        if not deleted:
            raise AttributeCategoryNotFoundError(category_id=category_id)

        return DeleteAttributeCategoryResult(category_id=category_id, deleted=True)

    async def list_attribute_categories(
        self,
        *,
        status: AttributeCategoryListStatus = AttributeCategoryListStatus.ACTIVE,
    ) -> AttributeCategoryList:
        categories = await self._category_repository.list(active_only=False)
        active_categories = tuple(category for category in categories if category.is_active)
        inactive_categories = tuple(category for category in categories if not category.is_active)

        if status == AttributeCategoryListStatus.ACTIVE:
            filtered_categories = active_categories
        elif status == AttributeCategoryListStatus.INACTIVE:
            filtered_categories = inactive_categories
        else:
            filtered_categories = categories

        return AttributeCategoryList(
            categories=filtered_categories,
            total_count=len(categories),
            active_count=len(active_categories),
            inactive_count=len(inactive_categories),
            status=status,
        )


def _validated_attribute_category_id(category_id: str | UUID) -> UUID | str:
    try:
        return UUID(str(category_id))
    except ValueError as error:
        try:
            return normalize_attribute_external_id(str(category_id))
        except ValueError as external_error:
            raise AttributeCategoryValidationError(message=str(external_error)) from error


def _resolve_update[T](value: T | PreserveAttributeCategoryField, existing_value: T) -> T:
    if isinstance(value, PreserveAttributeCategoryField):
        return existing_value

    return value


def _reject_protected_category_lifecycle(category: AttributeCategory) -> None:
    if category.external_id != ATTRIBUTE_CATEGORY_DEFAULT_EXTERNAL_ID:
        return

    raise AttributeCategoryProtectedError(
        category_id=category.id,
        external_id=category.external_id,
    )


def _create_category_external_id(command: CreateAttributeCategoryCommand) -> str:
    external_id = (
        command.external_id
        or command.id
        or _generated_category_external_id(
            command.label,
        )
    )
    return normalize_attribute_external_id(external_id)


def _generated_attribute_category_id(external_id: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"docmind:attribute-category:{external_id}")


def _generated_category_external_id(label: str) -> str:
    ascii_label = "".join(
        character for character in normalize("NFKD", label) if unicode_category(character) != "Mn"
    )
    normalized = sub(r"[^a-z0-9]+", "_", ascii_label.casefold()).strip("_")
    if not normalized:
        return "category_" + uuid5(NAMESPACE_URL, f"docmind:attribute-category:{label}").hex[:16]
    if len(normalized) <= 80:
        return normalized
    return (
        normalized[:63].rstrip("_")
        + "_"
        + uuid5(NAMESPACE_URL, f"docmind:attribute-category:{label}").hex[:16]
    )
