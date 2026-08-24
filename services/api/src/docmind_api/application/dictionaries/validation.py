"""Validation helpers for custom dictionary application workflows."""

from collections.abc import Mapping
from uuid import UUID

from docmind_api.application.dictionaries.commands import (
    DICTIONARY_ENTRY_LIST_MAX_LIMIT,
    DictionaryEntryListStatus,
    DictionaryListStatus,
    PreserveDictionaryField,
    SaveDictionaryFieldItem,
)
from docmind_api.application.dictionaries.errors import (
    DictionaryEntryValidationError,
    DictionaryValidationError,
    InactiveDictionaryMutationError,
)
from docmind_api.domain.dictionaries.models import (
    Dictionary,
    DictionaryEntry,
    DictionaryEntryScalar,
    DictionaryEntryValuesValidationError,
    DictionaryField,
    DictionaryStatus,
    normalize_dictionary_external_id,
    validate_dictionary_entry_values,
)


def validated_dictionary_reference(value: UUID | str) -> UUID | str:
    """Return a UUID or normalized business ID for a dictionary reference."""

    try:
        return UUID(str(value))
    except ValueError as error:
        try:
            return normalize_dictionary_external_id(str(value))
        except ValueError as external_error:
            raise DictionaryValidationError(message=str(external_error)) from error


def dictionary_status_filter(status: DictionaryListStatus) -> DictionaryStatus | None:
    """Return repository lifecycle filter for dictionary lists."""

    if status == DictionaryListStatus.ALL:
        return None
    return DictionaryStatus(status.value)


def entry_status_filter(status: DictionaryEntryListStatus) -> DictionaryStatus | None:
    """Return repository lifecycle filter for dictionary entry lists."""

    if status == DictionaryEntryListStatus.ALL:
        return None
    return DictionaryStatus(status.value)


def normalize_search(search: str | None) -> str | None:
    """Normalize blank search text to no search filter."""

    if search is None:
        return None
    normalized = search.strip()
    return normalized or None


def resolve_update[T](value: T | PreserveDictionaryField, existing_value: T) -> T:
    """Resolve update marker values against stored values."""

    if isinstance(value, PreserveDictionaryField):
        return existing_value
    return value


def duplicate_field_ids(fields: tuple[SaveDictionaryFieldItem, ...]) -> tuple[str, ...]:
    """Return duplicate normalized field external IDs."""

    normalized = [normalize_dictionary_external_id(field.external_id) for field in fields]
    return tuple(sorted({field_id for field_id in normalized if normalized.count(field_id) > 1}))


def require_active_dictionary(dictionary: Dictionary) -> None:
    """Raise when a dictionary cannot accept mutations."""

    if not dictionary.is_active:
        raise InactiveDictionaryMutationError(dictionary_id=dictionary.id)


def validated_entry_values(
    *,
    fields: tuple[DictionaryField, ...],
    values: Mapping[str, object],
    existing_entries: tuple[DictionaryEntry, ...],
    current_entry_id: UUID | None = None,
) -> dict[str, DictionaryEntryScalar]:
    """Validate typed dictionary entry values and adapt domain errors."""

    try:
        return dict(
            validate_dictionary_entry_values(
                fields=fields,
                values=values,
                existing_entries=existing_entries,
                current_entry_id=current_entry_id,
            ),
        )
    except DictionaryEntryValuesValidationError as error:
        raise DictionaryEntryValidationError(
            message=str(error),
            details=error.as_details(),
        ) from error


def validate_entry_page_window(*, limit: int, offset: int) -> None:
    """Validate dictionary entry paging boundaries."""

    if limit < 1 or limit > DICTIONARY_ENTRY_LIST_MAX_LIMIT:
        raise DictionaryValidationError(
            message=(
                "Dictionary entry list limit must be between 1 and "
                f"{DICTIONARY_ENTRY_LIST_MAX_LIMIT}."
            ),
            details={"limit": limit, "max_limit": DICTIONARY_ENTRY_LIST_MAX_LIMIT},
        )
    if offset < 0:
        raise DictionaryValidationError(
            message="Dictionary entry list offset cannot be negative.",
            details={"offset": offset},
        )
