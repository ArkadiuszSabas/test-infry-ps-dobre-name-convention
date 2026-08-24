"""Framework-free OCR pipeline configuration models."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Any
from uuid import UUID

OCR_PIPELINE_NAME_MAX_LENGTH = 200
OCR_PIPELINE_DESCRIPTION_MAX_LENGTH = 2000
OCR_PIPELINE_STEP_ID_MAX_LENGTH = 80
OCR_PIPELINE_IMPLEMENTATION_ID_MAX_LENGTH = 160
OCR_PIPELINE_DISPLAY_NAME_MAX_LENGTH = 200
OCR_PIPELINE_BLOCK_VERSION_MAX_LENGTH = 80
OCR_PIPELINE_CATEGORY_MAX_LENGTH = 80
OCR_PIPELINE_ARTIFACT_KEY_MAX_LENGTH = 160


class OcrPipelineKind(StrEnum):
    """Supported pipeline topology kinds."""

    LINEAR = "linear"


class OcrPipelineFailurePolicy(StrEnum):
    """Supported behavior when one pipeline step fails."""

    REQUIRED = "required"
    OPTIONAL = "optional"


class OcrPipelineLifecycle(StrEnum):
    """Lifecycle summary for an OCR pipeline definition."""

    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class OcrPipelineAuditAction(StrEnum):
    """Auditable lifecycle and configuration actions."""

    CREATED = "created"
    DRAFT_UPDATED = "draft_updated"
    VALIDATED = "validated"
    PUBLISHED = "published"
    ARCHIVED = "archived"
    DELETED = "deleted"
    DEFAULT_CHANGED = "default_changed"


class OcrPipelineBlockStatus(StrEnum):
    """Availability status returned for one LLM Magic pipeline block."""

    AVAILABLE = "available"
    DISABLED = "disabled"
    PLANNED = "planned"
    DEPRECATED = "deprecated"


class OcrPipelineDiagnosticSeverity(StrEnum):
    """Validation diagnostic severity."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


type JsonObject = Mapping[str, Any]


def _empty_mapping() -> Mapping[str, Any]:
    return MappingProxyType({})


@dataclass(frozen=True, slots=True)
class OcrPipelineDiagnostic:
    """API-safe diagnostic returned by product or technical validation."""

    severity: OcrPipelineDiagnosticSeverity
    code: str
    message: str
    path: str | None = None
    step_id: str | None = None

    @property
    def is_error(self) -> bool:
        """Return whether this diagnostic blocks publication."""

        return self.severity == OcrPipelineDiagnosticSeverity.ERROR

    def as_details(self) -> dict[str, str | None]:
        """Return a JSON-safe representation for error details."""

        return {
            "severity": self.severity.value,
            "code": self.code,
            "path": self.path,
            "step_id": self.step_id,
            "message": self.message,
        }


@dataclass(frozen=True, slots=True)
class OcrPipelineStepDefinition:
    """One ordered OCR pipeline builder step."""

    step_id: str
    implementation_id: str
    display_name: str
    enabled: bool = True
    failure_policy: OcrPipelineFailurePolicy = OcrPipelineFailurePolicy.REQUIRED
    config: JsonObject = field(default_factory=_empty_mapping)

    def __post_init__(self) -> None:
        object.__setattr__(self, "step_id", _normalize_required_text("step_id", self.step_id))
        object.__setattr__(
            self,
            "implementation_id",
            _normalize_required_text("implementation_id", self.implementation_id),
        )
        object.__setattr__(
            self,
            "display_name",
            _normalize_required_text("display_name", self.display_name),
        )
        _check_max_length("step_id", self.step_id, OCR_PIPELINE_STEP_ID_MAX_LENGTH)
        _check_max_length(
            "implementation_id",
            self.implementation_id,
            OCR_PIPELINE_IMPLEMENTATION_ID_MAX_LENGTH,
        )
        _check_max_length(
            "display_name",
            self.display_name,
            OCR_PIPELINE_DISPLAY_NAME_MAX_LENGTH,
        )
        object.__setattr__(self, "config", MappingProxyType(dict(self.config)))


@dataclass(frozen=True, slots=True)
class OcrPipelineDraftDefinition:
    """Editable API-owned OCR pipeline definition shape."""

    name: str
    description: str | None = None
    steps: tuple[OcrPipelineStepDefinition, ...] = ()
    schema_version: int = 1
    kind: OcrPipelineKind = OcrPipelineKind.LINEAR

    def __post_init__(self) -> None:
        if self.schema_version != 1:
            raise ValueError("OCR pipeline schema_version must be 1.")
        object.__setattr__(self, "name", normalize_ocr_pipeline_name(self.name))
        object.__setattr__(
            self,
            "description",
            normalize_ocr_pipeline_description(self.description),
        )
        object.__setattr__(self, "steps", tuple(self.steps))


@dataclass(frozen=True, slots=True)
class OcrPipelineBlockMetadata:
    """API-safe block metadata exposed to the admin builder."""

    implementation_id: str
    step_type: str
    display_name: str
    status: OcrPipelineBlockStatus
    category: str
    version: str
    description: str | None = None
    requires: tuple[str, ...] = ()
    produces: tuple[str, ...] = ()
    default_config: JsonObject = field(default_factory=_empty_mapping)
    config_schema: JsonObject = field(default_factory=_empty_mapping)
    ui_hints: JsonObject = field(default_factory=_empty_mapping)
    allowed_failure_policies: tuple[OcrPipelineFailurePolicy, ...] = (
        OcrPipelineFailurePolicy.REQUIRED,
    )
    disabled_reason: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "implementation_id",
            _normalize_required_text("implementation_id", self.implementation_id),
        )
        object.__setattr__(self, "step_type", _normalize_required_text("step_type", self.step_type))
        object.__setattr__(
            self,
            "display_name",
            _normalize_required_text("display_name", self.display_name),
        )
        object.__setattr__(self, "category", _normalize_required_text("category", self.category))
        object.__setattr__(self, "version", _normalize_required_text("version", self.version))
        _check_max_length(
            "implementation_id",
            self.implementation_id,
            OCR_PIPELINE_IMPLEMENTATION_ID_MAX_LENGTH,
        )
        _check_max_length("display_name", self.display_name, OCR_PIPELINE_DISPLAY_NAME_MAX_LENGTH)
        _check_max_length("category", self.category, OCR_PIPELINE_CATEGORY_MAX_LENGTH)
        _check_max_length("version", self.version, OCR_PIPELINE_BLOCK_VERSION_MAX_LENGTH)
        object.__setattr__(
            self, "description", normalize_ocr_pipeline_description(self.description)
        )
        object.__setattr__(self, "requires", _normalized_artifact_keys(self.requires))
        object.__setattr__(self, "produces", _normalized_artifact_keys(self.produces))
        object.__setattr__(self, "default_config", MappingProxyType(dict(self.default_config)))
        object.__setattr__(self, "config_schema", MappingProxyType(dict(self.config_schema)))
        object.__setattr__(self, "ui_hints", MappingProxyType(dict(self.ui_hints)))
        object.__setattr__(self, "allowed_failure_policies", tuple(self.allowed_failure_policies))
        if not self.allowed_failure_policies:
            raise ValueError("OCR pipeline block must allow at least one failure policy.")


@dataclass(frozen=True, slots=True)
class OcrPipelineBlockCatalog:
    """Block catalog plus stable catalog identity metadata."""

    blocks: tuple[OcrPipelineBlockMetadata, ...]
    catalog_version: str
    catalog_hash: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "blocks", tuple(self.blocks))
        object.__setattr__(
            self,
            "catalog_version",
            _normalize_required_text("catalog_version", self.catalog_version),
        )
        object.__setattr__(
            self,
            "catalog_hash",
            _normalize_required_text("catalog_hash", self.catalog_hash),
        )

    def by_implementation_id(self) -> dict[str, OcrPipelineBlockMetadata]:
        """Return block metadata keyed by implementation id."""

        return {block.implementation_id: block for block in self.blocks}


@dataclass(frozen=True, slots=True)
class OcrPipelineValidationResult:
    """Product and technical validation result."""

    diagnostics: tuple[OcrPipelineDiagnostic, ...] = ()
    compiled_snapshot: JsonObject | None = None
    catalog_version: str | None = None
    catalog_hash: str | None = None

    @property
    def valid(self) -> bool:
        """Return whether validation has no blocking error diagnostics."""

        return not any(diagnostic.is_error for diagnostic in self.diagnostics)


@dataclass(frozen=True, slots=True)
class OcrPipelineDefinitionRecord:
    """Persistable OCR pipeline aggregate as seen by the application layer."""

    id: UUID
    lifecycle: OcrPipelineLifecycle
    draft: OcrPipelineDraftDefinition | None
    created_at: datetime
    updated_at: datetime
    is_default: bool = False
    published_definition: OcrPipelineDraftDefinition | None = None
    published_version: int | None = None
    published_at: datetime | None = None
    archived_at: datetime | None = None
    last_validation: OcrPipelineValidationResult | None = None
    compiled_snapshot: JsonObject | None = None
    catalog_version: str | None = None
    catalog_hash: str | None = None

    @property
    def display_definition(self) -> OcrPipelineDraftDefinition | None:
        """Return the best available definition for list/detail display."""

        return self.draft or self.published_definition

    @property
    def has_published_version(self) -> bool:
        """Return whether this pipeline has ever been published."""

        return self.published_definition is not None and self.published_version is not None


def normalize_ocr_pipeline_name(value: str) -> str:
    """Validate and normalize an OCR pipeline display name."""

    normalized = _normalize_required_text("name", value)
    _check_max_length("name", normalized, OCR_PIPELINE_NAME_MAX_LENGTH)
    normalize_ocr_pipeline_name_key(normalized)
    return normalized


def normalize_ocr_pipeline_name_key(value: str) -> str:
    """Return the case-insensitive uniqueness key for an OCR pipeline name."""

    normalized = value.strip().casefold()
    if not normalized:
        raise ValueError("OCR pipeline normalized name is required.")
    _check_max_length("normalized name", normalized, OCR_PIPELINE_NAME_MAX_LENGTH)
    return normalized


def normalize_ocr_pipeline_description(value: str | None) -> str | None:
    """Validate and normalize an optional OCR pipeline description."""

    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    _check_max_length("description", normalized, OCR_PIPELINE_DESCRIPTION_MAX_LENGTH)
    return normalized


def _normalize_required_text(name: str, value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"OCR pipeline {name} is required.")
    return normalized


def _check_max_length(name: str, value: str, max_length: int) -> None:
    if len(value) > max_length:
        raise ValueError(f"OCR pipeline {name} cannot exceed {max_length} characters.")


def _normalized_artifact_keys(values: Sequence[str]) -> tuple[str, ...]:
    normalized_values: list[str] = []
    for value in values:
        normalized = _normalize_required_text("artifact key", value)
        _check_max_length("artifact key", normalized, OCR_PIPELINE_ARTIFACT_KEY_MAX_LENGTH)
        normalized_values.append(normalized)
    return tuple(normalized_values)
