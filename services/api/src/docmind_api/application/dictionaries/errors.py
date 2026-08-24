"""Application errors for custom dictionary use cases."""

from docmind_api.domain.dictionaries.models import DictionaryEntryUsage, DictionaryUsage
from docmind_backend_runtime.errors import (
    BusinessRuleError,
    ConflictError,
    NotFoundError,
    ValidationApplicationError,
)


class DictionaryAlreadyExistsError(ConflictError):
    """Raised when a dictionary external ID is already registered."""

    def __init__(self, *, external_id: str) -> None:
        super().__init__(
            code="DICTIONARY_ALREADY_EXISTS",
            message="Dictionary already exists.",
            details={"external_id": external_id},
        )


class DictionaryNotFoundError(NotFoundError):
    """Raised when a dictionary cannot be found."""

    def __init__(self, *, dictionary_id: object) -> None:
        super().__init__(
            code="DICTIONARY_NOT_FOUND",
            message="Dictionary not found.",
            details={"dictionary_id": str(dictionary_id)},
        )


class DictionaryEntryAlreadyExistsError(ConflictError):
    """Raised when a dictionary entry external ID is already registered."""

    def __init__(self, *, dictionary_id: object, external_id: str) -> None:
        super().__init__(
            code="DICTIONARY_ENTRY_ALREADY_EXISTS",
            message="Dictionary entry already exists.",
            details={"dictionary_id": str(dictionary_id), "external_id": external_id},
        )


class DictionaryEntryNotFoundError(NotFoundError):
    """Raised when a dictionary entry cannot be found."""

    def __init__(self, *, dictionary_id: object, entry_id: object) -> None:
        super().__init__(
            code="DICTIONARY_ENTRY_NOT_FOUND",
            message="Dictionary entry not found.",
            details={"dictionary_id": str(dictionary_id), "entry_id": str(entry_id)},
        )


class DictionaryEntryInUseError(ConflictError):
    """Raised when blocking dependencies prevent permanent entry deletion."""

    def __init__(
        self,
        *,
        dictionary_id: object,
        entry_id: object,
        usage: DictionaryEntryUsage,
    ) -> None:
        super().__init__(
            code="DICTIONARY_ENTRY_IN_USE",
            message="Dictionary entry is used and cannot be deleted.",
            details={
                "dictionary_id": str(dictionary_id),
                "entry_id": str(entry_id),
                "blocking_dependencies": usage.blocking_dependencies,
                "usage": usage.as_details(),
            },
        )


class DictionaryInUseError(ConflictError):
    """Raised when blocking dependencies prevent permanent dictionary deletion."""

    def __init__(self, *, dictionary_id: object, usage: DictionaryUsage) -> None:
        super().__init__(
            code="DICTIONARY_IN_USE",
            message="Dictionary is used and cannot be deleted.",
            details={
                "dictionary_id": str(dictionary_id),
                "blocking_dependencies": usage.blocking_dependencies,
                "usage": usage.as_details(),
            },
        )


class DictionaryFieldsInUseError(ConflictError):
    """Raised when entries block permanent dictionary field deletion."""

    def __init__(
        self,
        *,
        dictionary_id: object,
        removed_field_external_ids: tuple[str, ...],
        usage: DictionaryUsage,
    ) -> None:
        super().__init__(
            code="DICTIONARY_FIELDS_IN_USE",
            message="Dictionary fields cannot be removed while entries exist.",
            details={
                "dictionary_id": str(dictionary_id),
                "removed_field_external_ids": removed_field_external_ids,
                "usage": usage.as_details(),
            },
        )


class DictionaryUsedByActiveAttributeError(ConflictError):
    """Raised when active attribute bindings prevent dictionary deactivation."""

    def __init__(self, *, dictionary_id: object, usage: DictionaryUsage) -> None:
        super().__init__(
            code="DICTIONARY_USED_BY_ACTIVE_ATTRIBUTE",
            message="Dictionary is used by an active attribute definition.",
            details={"dictionary_id": str(dictionary_id), "usage": usage.as_details()},
        )


class DictionaryUsedByActiveSystemCatalogFieldError(ConflictError):
    """Raised when active system catalog fields prevent dictionary deactivation."""

    def __init__(self, *, dictionary_id: object, usage: DictionaryUsage) -> None:
        super().__init__(
            code="DICTIONARY_USED_BY_ACTIVE_SYSTEM_CATALOG_FIELD",
            message="Dictionary is used by an active system catalog field.",
            details={"dictionary_id": str(dictionary_id), "usage": usage.as_details()},
        )


class InactiveDictionaryMutationError(BusinessRuleError):
    """Raised when mutating fields or entries for an inactive dictionary."""

    def __init__(self, *, dictionary_id: object) -> None:
        super().__init__(
            code="DICTIONARY_INACTIVE",
            message="Dictionary is inactive and cannot accept new configuration changes.",
            details={"dictionary_id": str(dictionary_id)},
        )


class DictionaryValidationError(ValidationApplicationError):
    """Raised when dictionary command input is invalid."""

    def __init__(
        self,
        *,
        message: str,
        details: dict[str, object] | None = None,
    ) -> None:
        super().__init__(
            code="DICTIONARY_VALIDATION_ERROR",
            message=message,
            details=details,
        )


class DictionaryEntryValidationError(ValidationApplicationError):
    """Raised when dictionary entry values are invalid."""

    def __init__(
        self,
        *,
        message: str,
        details: dict[str, object] | None = None,
    ) -> None:
        super().__init__(
            code="DICTIONARY_ENTRY_VALIDATION_ERROR",
            message=message,
            details=details,
        )
