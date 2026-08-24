"""Document metadata validation issue models."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MissingRequiredMetadataField:
    """One required metadata field omitted from the submitted values."""

    id: str
    name: str

    def as_details(self) -> dict[str, str]:
        """Return the stable field identity and display name."""

        return {"id": self.id, "name": self.name}


@dataclass(frozen=True, slots=True)
class InvalidMetadataType:
    """One metadata value that cannot be stored as the expected JSON type."""

    field: str
    expected: str
    actual: str

    def as_details(self) -> dict[str, str]:
        """Return API-safe details for this issue."""

        return {"field": self.field, "expected": self.expected, "actual": self.actual}


@dataclass(frozen=True, slots=True)
class InvalidMetadataEnumValue:
    """One metadata value that violates configured allowed values."""

    field: str
    allowed_values: tuple[str, ...]
    actual: dict[str, object]
    code: str | None = None
    reason: str | None = None
    dictionary_id: str | None = None

    def as_details(self) -> dict[str, object]:
        """Return API-safe details for this issue."""

        details: dict[str, object] = {
            "field": self.field,
            "allowed_values": self.allowed_values,
            "actual": self.actual,
        }
        if self.code is not None:
            details["code"] = self.code
        if self.reason is not None:
            details["reason"] = self.reason
        if self.dictionary_id is not None:
            details["dictionary_id"] = self.dictionary_id

        return details


@dataclass(frozen=True, slots=True)
class InvalidMetadataConstraint:
    """One metadata value that violates a configured field constraint."""

    field: str
    constraint: str
    expected: object
    actual: dict[str, object]
    expected_length: int | None = None

    def as_details(self) -> dict[str, object]:
        """Return API-safe details for this issue."""

        details = {
            "field": self.field,
            "constraint": self.constraint,
            "expected": self.expected,
            "actual": self.actual,
        }
        if self.expected_length is not None:
            details["expected_length"] = self.expected_length

        return details


class DocumentMetadataValidationError(ValueError):
    """Raised when metadata values do not match the inherited document type schema."""

    def __init__(
        self,
        *,
        document_type_id: object,
        unknown_fields: tuple[str, ...] = (),
        missing_required_fields: tuple[MissingRequiredMetadataField, ...] = (),
        invalid_types: tuple[InvalidMetadataType, ...] = (),
        invalid_enum_values: tuple[InvalidMetadataEnumValue, ...] = (),
        constraint_violations: tuple[InvalidMetadataConstraint, ...] = (),
    ) -> None:
        super().__init__("Document metadata does not match the selected document type schema.")
        self.document_type_id = str(document_type_id)
        self.unknown_fields = unknown_fields
        self.missing_required_fields = missing_required_fields
        self.invalid_types = invalid_types
        self.invalid_enum_values = invalid_enum_values
        self.constraint_violations = constraint_violations

    def as_details(self) -> dict[str, object]:
        """Return API-safe validation details."""

        return {
            "document_type_id": self.document_type_id,
            "unknown_fields": self.unknown_fields,
            "missing_required_fields": tuple(
                field.as_details() for field in self.missing_required_fields
            ),
            "invalid_types": tuple(issue.as_details() for issue in self.invalid_types),
            "invalid_enum_values": tuple(issue.as_details() for issue in self.invalid_enum_values),
            "constraint_violations": tuple(
                issue.as_details() for issue in self.constraint_violations
            ),
        }
