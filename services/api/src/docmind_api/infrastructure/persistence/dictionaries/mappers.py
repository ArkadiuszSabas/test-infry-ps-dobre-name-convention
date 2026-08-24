"""Row mappers for custom dictionary persistence."""

from collections.abc import Mapping
from typing import Any, cast
from uuid import UUID

from docmind_api.domain.attributes.models import AttributeConstraints, AttributeDataType
from docmind_api.domain.dictionaries.models import (
    Dictionary,
    DictionaryEntry,
    DictionaryEntryScalar,
    DictionaryField,
    DictionaryStatus,
)


def dictionary_from_row(row: Mapping[Any, Any]) -> Dictionary:
    """Reconstruct a dictionary aggregate from a SQL row."""

    return Dictionary(
        id=row["id"],
        external_id=row["external_id"],
        name=row["name"],
        description=row["description"],
        status=DictionaryStatus(row["status"]),
        schema_version=row["schema_version"],
        entries_version=row["entries_version"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def field_from_row(row: Mapping[Any, Any]) -> DictionaryField:
    """Reconstruct a dictionary field from a SQL row."""

    return DictionaryField(
        id=row["id"],
        dictionary_id=row["dictionary_id"],
        external_id=row["external_id"],
        label=row["label"],
        data_type=AttributeDataType(row["data_type"]),
        required=bool(row["required"]),
        constraints=AttributeConstraints.from_mapping(cast(dict[str, object], row["constraints"])),
        normalization=cast(dict[str, object], row["normalization"]),
        format=cast(dict[str, object], row["format"]),
        is_unique=bool(row["is_unique"]),
        sort_order=row["sort_order"],
        status=DictionaryStatus(row["status"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def entry_from_row(row: Mapping[Any, Any]) -> DictionaryEntry:
    """Reconstruct a dictionary entry from a SQL row."""

    return DictionaryEntry(
        id=row["id"],
        dictionary_id=row["dictionary_id"],
        external_id=row["external_id"],
        label=row["label"],
        values=cast(dict[str, DictionaryEntryScalar], row["values"]),
        status=DictionaryStatus(row["status"]),
        sort_order=row["sort_order"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def coerce_uuid(value: UUID | str) -> UUID | None:
    """Return a UUID when a repository reference is a UUID string."""

    try:
        return UUID(str(value))
    except ValueError:
        return None
