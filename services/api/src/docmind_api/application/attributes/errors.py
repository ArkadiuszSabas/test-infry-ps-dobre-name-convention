"""Application errors for attribute catalog workflows."""

from docmind_api.domain.attributes.models import AttributeCategoryUsage, AttributeDefinitionUsage
from docmind_backend_runtime.errors import (
    ConflictError,
    NotFoundError,
    ValidationApplicationError,
)


class AttributeDefinitionAlreadyExistsError(ConflictError):
    def __init__(
        self,
        *,
        external_id: str | None = None,
        attribute_id: str | None = None,
    ) -> None:
        external_id_value = external_id or attribute_id or ""
        super().__init__(
            code="ATTRIBUTE_DEFINITION_ALREADY_EXISTS",
            message="Attribute definition already exists.",
            details={"external_id": external_id_value},
        )
        self.external_id = external_id_value


class AttributeDefinitionNotFoundError(NotFoundError):
    def __init__(self, *, attribute_id: object) -> None:
        attribute_id_value = str(attribute_id)
        super().__init__(
            code="ATTRIBUTE_DEFINITION_NOT_FOUND",
            message="Attribute definition not found.",
            details={"attribute_id": attribute_id_value},
        )
        self.attribute_id = attribute_id_value


class AttributeDefinitionInUseError(ConflictError):
    def __init__(self, *, attribute_id: object, usage: AttributeDefinitionUsage) -> None:
        attribute_id_value = str(attribute_id)
        super().__init__(
            code="ATTRIBUTE_DEFINITION_IN_USE",
            message="Attribute definition is used and cannot be deleted.",
            details={
                "attribute_id": attribute_id_value,
                "blocking_dependencies": tuple(usage.blocking_dependencies),
                "usage": usage.as_details(),
            },
        )
        self.attribute_id = attribute_id_value


class AttributeDefinitionUsedByActiveDocumentTypeError(ConflictError):
    def __init__(self, *, attribute_id: object, usage: AttributeDefinitionUsage) -> None:
        attribute_id_value = str(attribute_id)
        super().__init__(
            code="ATTRIBUTE_DEFINITION_USED_BY_ACTIVE_DOCUMENT_TYPE",
            message="Attribute definition is used by an active document type.",
            details={
                "attribute_id": attribute_id_value,
                "usage": usage.as_details(),
            },
        )
        self.attribute_id = attribute_id_value


class AttributeDefinitionUsedByActiveConfigurationError(ConflictError):
    def __init__(self, *, attribute_id: object, usage: AttributeDefinitionUsage) -> None:
        attribute_id_value = str(attribute_id)
        super().__init__(
            code="ATTRIBUTE_DEFINITION_USED_BY_ACTIVE_CONFIGURATION",
            message="Attribute definition is used by an active configuration.",
            details={
                "attribute_id": attribute_id_value,
                "usage": usage.as_details(),
            },
        )
        self.attribute_id = attribute_id_value


class AttributeDefinitionValidationError(ValidationApplicationError):
    def __init__(
        self,
        *,
        message: str,
        details: dict[str, object] | None = None,
    ) -> None:
        super().__init__(
            code="ATTRIBUTE_DEFINITION_VALIDATION_ERROR",
            message=message,
            details=details,
        )


class AttributeCategoryAlreadyExistsError(ConflictError):
    def __init__(
        self,
        *,
        external_id: str | None = None,
        category_id: str | None = None,
    ) -> None:
        external_id_value = external_id or category_id or ""
        super().__init__(
            code="ATTRIBUTE_CATEGORY_ALREADY_EXISTS",
            message="Attribute category already exists.",
            details={"external_id": external_id_value},
        )
        self.external_id = external_id_value


class AttributeCategoryNotFoundError(NotFoundError):
    def __init__(self, *, category_id: object) -> None:
        category_id_value = str(category_id)
        super().__init__(
            code="ATTRIBUTE_CATEGORY_NOT_FOUND",
            message="Attribute category not found.",
            details={"category_id": category_id_value},
        )
        self.category_id = category_id_value


class AttributeCategoryInUseError(ConflictError):
    def __init__(self, *, category_id: object, usage: AttributeCategoryUsage) -> None:
        category_id_value = str(category_id)
        super().__init__(
            code="ATTRIBUTE_CATEGORY_IN_USE",
            message="Attribute category is used and cannot be deleted.",
            details={
                "category_id": category_id_value,
                "blocking_dependencies": tuple(usage.blocking_dependencies),
                "usage": usage.as_details(),
            },
        )
        self.category_id = category_id_value


class AttributeCategoryUsedByActiveAttributeError(ConflictError):
    def __init__(self, *, category_id: object, usage: AttributeCategoryUsage) -> None:
        category_id_value = str(category_id)
        super().__init__(
            code="ATTRIBUTE_CATEGORY_USED_BY_ACTIVE_ATTRIBUTE",
            message="Attribute category is used by an active attribute.",
            details={
                "category_id": category_id_value,
                "usage": usage.as_details(),
            },
        )
        self.category_id = category_id_value


class AttributeCategoryProtectedError(ConflictError):
    def __init__(self, *, category_id: object, external_id: str) -> None:
        category_id_value = str(category_id)
        super().__init__(
            code="ATTRIBUTE_CATEGORY_PROTECTED",
            message="Attribute category is protected and cannot be deactivated or deleted.",
            details={
                "category_id": category_id_value,
                "external_id": external_id,
            },
        )
        self.category_id = category_id_value
        self.external_id = external_id


class AttributeCategoryValidationError(ValidationApplicationError):
    def __init__(
        self,
        *,
        message: str,
        details: dict[str, object] | None = None,
    ) -> None:
        super().__init__(
            code="ATTRIBUTE_CATEGORY_VALIDATION_ERROR",
            message=message,
            details=details,
        )
