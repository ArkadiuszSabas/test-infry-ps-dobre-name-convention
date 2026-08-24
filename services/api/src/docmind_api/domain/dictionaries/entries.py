"""Custom dictionary entry entity."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType
from uuid import NAMESPACE_URL, UUID, uuid5

from docmind_api.domain.dictionaries.constants import (
    DICTIONARY_ENTRY_LABEL_MAX_LENGTH,
    DICTIONARY_SORT_ORDER_MIN,
)
from docmind_api.domain.dictionaries.enums import DictionaryStatus
from docmind_api.domain.dictionaries.identifiers import normalize_dictionary_external_id

type DictionaryEntryScalar = str | int | float | bool | None


@dataclass(frozen=True, slots=True)
class DictionaryEntry:
    """One managed value inside a custom dictionary."""

    id: UUID | str
    dictionary_id: UUID | str
    external_id: str
    label: str
    values: Mapping[str, DictionaryEntryScalar]
    status: DictionaryStatus
    sort_order: int | None
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", _normalize_uuid(self.id, "dictionary-entry"))
        object.__setattr__(
            self,
            "dictionary_id",
            _normalize_uuid(self.dictionary_id, "dictionary"),
        )
        object.__setattr__(
            self,
            "external_id",
            normalize_dictionary_external_id(self.external_id),
        )
        object.__setattr__(self, "label", normalize_dictionary_entry_label(self.label))
        object.__setattr__(self, "values", MappingProxyType(_normalize_values(self.values)))
        object.__setattr__(self, "status", DictionaryStatus(self.status))
        if self.sort_order is not None:
            if type(self.sort_order) is not int:
                raise ValueError("Dictionary entry sort_order must be an integer.")
            if self.sort_order < DICTIONARY_SORT_ORDER_MIN:
                raise ValueError("Dictionary entry sort_order cannot be negative.")
        if self.created_at > self.updated_at:
            raise ValueError("Dictionary entry updated_at cannot be before created_at.")

    @property
    def is_active(self) -> bool:
        """Return whether this entry can be selected for new metadata values."""

        return self.status == DictionaryStatus.ACTIVE

    def update_business_fields(
        self,
        *,
        external_id: str,
        label: str,
        values: Mapping[str, DictionaryEntryScalar],
        sort_order: int | None,
        updated_at: datetime,
    ) -> DictionaryEntry:
        """Return this entry with editable fields changed."""

        return DictionaryEntry(
            id=self.id,
            dictionary_id=self.dictionary_id,
            external_id=external_id,
            label=label,
            values=values,
            status=self.status,
            sort_order=sort_order,
            created_at=self.created_at,
            updated_at=updated_at,
        )

    def deactivate(self, *, updated_at: datetime) -> DictionaryEntry:
        """Return this entry with inactive status."""

        return DictionaryEntry(
            id=self.id,
            dictionary_id=self.dictionary_id,
            external_id=self.external_id,
            label=self.label,
            values=self.values,
            status=DictionaryStatus.INACTIVE,
            sort_order=self.sort_order,
            created_at=self.created_at,
            updated_at=updated_at,
        )


def normalize_dictionary_entry_label(value: str) -> str:
    """Validate and return a dictionary entry display label."""

    normalized = value.strip()
    if not normalized:
        raise ValueError("Dictionary entry label is required.")
    if len(normalized) > DICTIONARY_ENTRY_LABEL_MAX_LENGTH:
        raise ValueError(
            f"Dictionary entry label cannot exceed {DICTIONARY_ENTRY_LABEL_MAX_LENGTH} characters.",
        )

    return normalized


def _normalize_values(
    values: Mapping[str, DictionaryEntryScalar],
) -> dict[str, DictionaryEntryScalar]:
    normalized: dict[str, DictionaryEntryScalar] = {}
    for key, value in values.items():
        normalized_key = normalize_dictionary_external_id(key)
        if isinstance(value, float) and value != value:
            raise ValueError("Dictionary entry values cannot contain non-finite numbers.")
        normalized[normalized_key] = value

    return normalized


def _normalize_uuid(value: UUID | str, namespace: str) -> UUID:
    try:
        return UUID(str(value))
    except ValueError:
        return uuid5(NAMESPACE_URL, f"docmind:{namespace}:{value}")
