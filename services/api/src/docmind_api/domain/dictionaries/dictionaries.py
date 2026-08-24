"""Custom dictionary catalog entity."""

from dataclasses import dataclass
from datetime import datetime
from uuid import NAMESPACE_URL, UUID, uuid5

from docmind_api.domain.dictionaries.constants import (
    DICTIONARY_DESCRIPTION_MAX_LENGTH,
    DICTIONARY_NAME_MAX_LENGTH,
)
from docmind_api.domain.dictionaries.enums import DictionaryStatus
from docmind_api.domain.dictionaries.identifiers import normalize_dictionary_external_id


@dataclass(frozen=True, slots=True)
class Dictionary:
    """A managed, deployment-local custom dictionary."""

    id: UUID | str
    external_id: str
    name: str
    description: str | None
    status: DictionaryStatus
    schema_version: int
    entries_version: int
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        try:
            normalized_id = UUID(str(self.id))
        except ValueError:
            normalized_id = uuid5(NAMESPACE_URL, f"docmind:dictionary:{self.id}")
        object.__setattr__(self, "id", normalized_id)
        object.__setattr__(
            self,
            "external_id",
            normalize_dictionary_external_id(self.external_id),
        )
        object.__setattr__(self, "name", normalize_dictionary_name(self.name))
        object.__setattr__(
            self,
            "description",
            normalize_dictionary_description(self.description),
        )
        object.__setattr__(self, "status", DictionaryStatus(self.status))
        object.__setattr__(
            self,
            "schema_version",
            normalize_dictionary_version(self.schema_version, field_name="schema_version"),
        )
        object.__setattr__(
            self,
            "entries_version",
            normalize_dictionary_version(self.entries_version, field_name="entries_version"),
        )
        if self.created_at > self.updated_at:
            raise ValueError("Dictionary updated_at cannot be before created_at.")

    @property
    def is_active(self) -> bool:
        """Return whether this dictionary can be used by new configuration."""

        return self.status == DictionaryStatus.ACTIVE

    def update_business_fields(
        self,
        *,
        name: str,
        description: str | None,
        updated_at: datetime,
    ) -> Dictionary:
        """Return this dictionary with editable business fields changed."""

        return Dictionary(
            id=self.id,
            external_id=self.external_id,
            name=name,
            description=description,
            status=self.status,
            schema_version=self.schema_version,
            entries_version=self.entries_version,
            created_at=self.created_at,
            updated_at=updated_at,
        )

    def deactivate(self, *, updated_at: datetime) -> Dictionary:
        """Return this dictionary with inactive status."""

        return Dictionary(
            id=self.id,
            external_id=self.external_id,
            name=self.name,
            description=self.description,
            status=DictionaryStatus.INACTIVE,
            schema_version=self.schema_version,
            entries_version=self.entries_version,
            created_at=self.created_at,
            updated_at=updated_at,
        )

    def bump_schema_version(self, *, updated_at: datetime) -> Dictionary:
        """Return this dictionary after a schema change."""

        return Dictionary(
            id=self.id,
            external_id=self.external_id,
            name=self.name,
            description=self.description,
            status=self.status,
            schema_version=self.schema_version + 1,
            entries_version=self.entries_version,
            created_at=self.created_at,
            updated_at=updated_at,
        )

    def bump_entries_version(self, *, updated_at: datetime) -> Dictionary:
        """Return this dictionary after entry membership or labels change."""

        return Dictionary(
            id=self.id,
            external_id=self.external_id,
            name=self.name,
            description=self.description,
            status=self.status,
            schema_version=self.schema_version,
            entries_version=self.entries_version + 1,
            created_at=self.created_at,
            updated_at=updated_at,
        )


def normalize_dictionary_name(value: str) -> str:
    """Validate and return a dictionary display name."""

    normalized = value.strip()
    if not normalized:
        raise ValueError("Dictionary name is required.")
    if len(normalized) > DICTIONARY_NAME_MAX_LENGTH:
        raise ValueError(
            f"Dictionary name cannot exceed {DICTIONARY_NAME_MAX_LENGTH} characters.",
        )

    return normalized


def normalize_dictionary_description(value: str | None) -> str | None:
    """Validate and return an optional dictionary description."""

    if value is None:
        return None

    normalized = value.strip()
    if not normalized:
        return None
    if len(normalized) > DICTIONARY_DESCRIPTION_MAX_LENGTH:
        raise ValueError(
            f"Dictionary description cannot exceed {DICTIONARY_DESCRIPTION_MAX_LENGTH} characters.",
        )

    return normalized


def normalize_dictionary_version(value: object, *, field_name: str) -> int:
    """Validate and return a positive dictionary version."""

    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"Dictionary {field_name} must be an integer.")
    if value < 1:
        raise ValueError(f"Dictionary {field_name} must be positive.")

    return value
