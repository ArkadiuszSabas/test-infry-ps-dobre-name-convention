"""Command and query models for custom dictionary use cases."""

from dataclasses import dataclass, field
from enum import StrEnum
from uuid import UUID

from docmind_api.application.listing import ListPage, ListSortDirection
from docmind_api.domain.attributes.models import AttributeConstraints, AttributeDataType
from docmind_api.domain.dictionaries.models import (
    Dictionary,
    DictionaryEntry,
    DictionaryEntryScalar,
    DictionaryStatus,
)

DICTIONARY_ENTRY_LIST_DEFAULT_LIMIT = 50
DICTIONARY_ENTRY_LIST_MAX_LIMIT = 100


def _empty_object_dict() -> dict[str, object]:
    return {}


class DictionaryListStatus(StrEnum):
    """Dictionary lifecycle filter accepted by list use cases."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    ALL = "all"


class DictionarySortField(StrEnum):
    """Safe sort keys exposed by the dictionary catalog."""

    NAME = "name"
    EXTERNAL_ID = "external_id"
    STATUS = "status"
    UPDATED_AT = "updated_at"


class DictionaryEntryListStatus(StrEnum):
    """Dictionary entry lifecycle filter accepted by lookup use cases."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    ALL = "all"


class DictionaryEntrySortField(StrEnum):
    """Safe sort keys exposed by the dictionary-entry collection."""

    CREATED_AT = "created_at"
    EXTERNAL_ID = "external_id"
    LABEL = "label"
    SORT_ORDER = "sort_order"
    STATUS = "status"
    UPDATED_AT = "updated_at"


@dataclass(frozen=True, slots=True)
class CreateDictionaryCommand:
    """Input for creating a custom dictionary."""

    external_id: str
    name: str
    description: str | None = None


@dataclass(frozen=True, slots=True)
class ListDictionariesQuery:
    """Input for listing custom dictionaries."""

    status: DictionaryListStatus = DictionaryListStatus.ACTIVE
    search: str | None = None
    sort_by: DictionarySortField = DictionarySortField.NAME
    sort_direction: ListSortDirection = ListSortDirection.ASC
    limit: int = 50
    offset: int = 0


@dataclass(frozen=True, slots=True)
class DictionaryListPageResult:
    """Paged dictionary catalog plus lifecycle facets."""

    page: ListPage[Dictionary]
    active_count: int
    inactive_count: int
    status: DictionaryListStatus


class PreserveDictionaryField:
    """Marker for update commands that keep a stored field unchanged."""

    __slots__ = ()


PRESERVE_DICTIONARY_FIELD = PreserveDictionaryField()
type DictionaryNameUpdate = str | PreserveDictionaryField
type DictionaryDescriptionUpdate = str | None | PreserveDictionaryField
type DictionaryEntryExternalIdUpdate = str | PreserveDictionaryField
type DictionaryEntryLabelUpdate = str | PreserveDictionaryField
type DictionaryEntryValuesUpdate = dict[str, DictionaryEntryScalar] | PreserveDictionaryField
type DictionaryEntrySortOrderUpdate = int | None | PreserveDictionaryField


@dataclass(frozen=True, slots=True)
class UpdateDictionaryCommand:
    """Input for editing dictionary business fields."""

    dictionary_id: UUID | str
    name: DictionaryNameUpdate = PRESERVE_DICTIONARY_FIELD
    description: DictionaryDescriptionUpdate = PRESERVE_DICTIONARY_FIELD


@dataclass(frozen=True, slots=True)
class DeactivateDictionaryCommand:
    """Input for deactivating a dictionary."""

    dictionary_id: UUID | str


@dataclass(frozen=True, slots=True)
class DeleteDictionaryCommand:
    """Input for permanently deleting an unused dictionary."""

    dictionary_id: UUID | str


@dataclass(frozen=True, slots=True)
class DeleteDictionaryResult:
    """Result of permanently deleting an unused dictionary."""

    dictionary_id: UUID
    deleted: bool


@dataclass(frozen=True, slots=True)
class SaveDictionaryFieldItem:
    """One submitted dictionary field schema row."""

    external_id: str
    label: str
    data_type: AttributeDataType
    required: bool = False
    constraints: AttributeConstraints = field(default_factory=AttributeConstraints)
    normalization: dict[str, object] = field(default_factory=_empty_object_dict)
    format: dict[str, object] = field(default_factory=_empty_object_dict)
    is_unique: bool = False
    sort_order: int = 0
    status: DictionaryStatus = DictionaryStatus.ACTIVE


@dataclass(frozen=True, slots=True)
class SaveDictionaryFieldsCommand:
    """Input for replacing a dictionary field schema."""

    dictionary_id: UUID | str
    fields: tuple[SaveDictionaryFieldItem, ...]


@dataclass(frozen=True, slots=True)
class CreateDictionaryEntryCommand:
    """Input for creating a dictionary entry."""

    dictionary_id: UUID | str
    external_id: str
    label: str
    values: dict[str, DictionaryEntryScalar]
    sort_order: int | None = None


@dataclass(frozen=True, slots=True)
class UpdateDictionaryEntryCommand:
    """Input for editing a dictionary entry."""

    dictionary_id: UUID | str
    entry_id: UUID | str
    external_id: DictionaryEntryExternalIdUpdate = PRESERVE_DICTIONARY_FIELD
    label: DictionaryEntryLabelUpdate = PRESERVE_DICTIONARY_FIELD
    values: DictionaryEntryValuesUpdate = PRESERVE_DICTIONARY_FIELD
    sort_order: DictionaryEntrySortOrderUpdate = PRESERVE_DICTIONARY_FIELD


@dataclass(frozen=True, slots=True)
class DeactivateDictionaryEntryCommand:
    """Input for deactivating a dictionary entry."""

    dictionary_id: UUID | str
    entry_id: UUID | str


@dataclass(frozen=True, slots=True)
class DeleteDictionaryEntryCommand:
    """Input for permanently deleting one dictionary entry."""

    dictionary_id: UUID | str
    entry_id: UUID | str


@dataclass(frozen=True, slots=True)
class DeleteDictionaryEntryResult:
    """Result of permanently deleting one dictionary entry."""

    entry_id: UUID
    deleted: bool


@dataclass(frozen=True, slots=True)
class ListDictionaryEntriesQuery:
    """Input for paged dictionary entry lookup."""

    dictionary_id: UUID | str
    status: DictionaryEntryListStatus = DictionaryEntryListStatus.ACTIVE
    search: str | None = None
    limit: int = DICTIONARY_ENTRY_LIST_DEFAULT_LIMIT
    offset: int = 0
    sort_by: DictionaryEntrySortField = DictionaryEntrySortField.SORT_ORDER
    sort_direction: ListSortDirection = ListSortDirection.ASC


@dataclass(frozen=True, slots=True)
class LookupDictionaryEntriesQuery:
    """Input for review-safe active dictionary entry lookup."""

    dictionary_id: UUID | str
    search: str | None = None
    limit: int = DICTIONARY_ENTRY_LIST_DEFAULT_LIMIT
    offset: int = 0


@dataclass(frozen=True, slots=True)
class ResolveDictionaryEntryQuery:
    """Input for resolving one current dictionary value by external ID."""

    dictionary_id: UUID | str
    entry_external_id: str


@dataclass(frozen=True, slots=True)
class DictionaryEntryPage:
    """Paged dictionary entry lookup result."""

    entries: tuple[DictionaryEntry, ...]
    total_count: int
    limit: int
    offset: int

    @property
    def returned_count(self) -> int:
        """Return number of entries in this page."""

        return len(self.entries)

    @property
    def has_more(self) -> bool:
        """Return whether another page is available."""

        return self.offset + self.returned_count < self.total_count
