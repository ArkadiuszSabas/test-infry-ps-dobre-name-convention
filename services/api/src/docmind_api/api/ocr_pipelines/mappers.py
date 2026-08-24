"""Response schema mapping helpers for OCR pipeline routes."""

from docmind_api.api.ocr_pipelines.schemas import (
    OcrPipelineBlockCatalogSchema,
    OcrPipelineBlockSchema,
    OcrPipelineDefinitionSchema,
    OcrPipelineDetailSchema,
    OcrPipelineDiagnosticSchema,
    OcrPipelineStepSchema,
    OcrPipelineSummarySchema,
    OcrPipelineValidationSchema,
)
from docmind_api.domain.ocr_pipelines.models import (
    OcrPipelineBlockCatalog,
    OcrPipelineDefinitionRecord,
    OcrPipelineDiagnostic,
    OcrPipelineDraftDefinition,
    OcrPipelineStepDefinition,
    OcrPipelineValidationResult,
)


def to_pipeline_detail_schema(record: OcrPipelineDefinitionRecord) -> OcrPipelineDetailSchema:
    """Map a pipeline aggregate to its detail response schema."""

    return OcrPipelineDetailSchema(
        id=record.id,
        lifecycle=record.lifecycle,
        is_default=record.is_default,
        draft=to_definition_schema(record.draft),
        published_definition=to_definition_schema(record.published_definition),
        published_version=record.published_version,
        last_validation=(
            to_validation_schema(record.last_validation)
            if record.last_validation is not None
            else None
        ),
        compiled_snapshot=(
            dict(record.compiled_snapshot) if record.compiled_snapshot is not None else None
        ),
        catalog_version=record.catalog_version,
        catalog_hash=record.catalog_hash,
        created_at=record.created_at,
        updated_at=record.updated_at,
        published_at=record.published_at,
        archived_at=record.archived_at,
    )


def to_pipeline_summary_schema(record: OcrPipelineDefinitionRecord) -> OcrPipelineSummarySchema:
    """Map a pipeline aggregate to its list-row response schema."""

    definition = record.display_definition
    return OcrPipelineSummarySchema(
        id=record.id,
        name=definition.name if definition is not None else "",
        description=definition.description if definition is not None else None,
        lifecycle=record.lifecycle,
        is_default=record.is_default,
        has_draft=record.draft is not None,
        published_version=record.published_version,
        last_validation_valid=(
            record.last_validation.valid if record.last_validation is not None else None
        ),
        created_at=record.created_at,
        updated_at=record.updated_at,
        published_at=record.published_at,
        archived_at=record.archived_at,
    )


def to_definition_schema(
    definition: OcrPipelineDraftDefinition | None,
) -> OcrPipelineDefinitionSchema | None:
    """Map a draft/published definition to its response schema."""

    if definition is None:
        return None
    return OcrPipelineDefinitionSchema(
        schema_version=definition.schema_version,
        kind=definition.kind,
        name=definition.name,
        description=definition.description,
        steps=[to_step_schema(step) for step in definition.steps],
    )


def to_step_schema(step: OcrPipelineStepDefinition) -> OcrPipelineStepSchema:
    """Map one domain step to its response schema."""

    return OcrPipelineStepSchema(
        step_id=step.step_id,
        implementation_id=step.implementation_id,
        display_name=step.display_name,
        enabled=step.enabled,
        failure_policy=step.failure_policy,
        config=dict(step.config),
    )


def to_validation_schema(validation: OcrPipelineValidationResult) -> OcrPipelineValidationSchema:
    """Map validation diagnostics to their response schema."""

    return OcrPipelineValidationSchema(
        valid=validation.valid,
        diagnostics=[to_diagnostic_schema(diagnostic) for diagnostic in validation.diagnostics],
        catalog_version=validation.catalog_version,
        catalog_hash=validation.catalog_hash,
        compiled_snapshot=(
            dict(validation.compiled_snapshot) if validation.compiled_snapshot is not None else None
        ),
    )


def to_diagnostic_schema(diagnostic: OcrPipelineDiagnostic) -> OcrPipelineDiagnosticSchema:
    """Map one validation diagnostic to its response schema."""

    return OcrPipelineDiagnosticSchema(
        severity=diagnostic.severity,
        code=diagnostic.code,
        path=diagnostic.path,
        step_id=diagnostic.step_id,
        message=diagnostic.message,
    )


def to_block_catalog_schema(catalog: OcrPipelineBlockCatalog) -> OcrPipelineBlockCatalogSchema:
    """Map a block catalog to its response schema."""

    return OcrPipelineBlockCatalogSchema(
        catalog_version=catalog.catalog_version,
        catalog_hash=catalog.catalog_hash,
        blocks=[
            OcrPipelineBlockSchema(
                implementation_id=block.implementation_id,
                step_type=block.step_type,
                display_name=block.display_name,
                description=block.description,
                status=block.status,
                category=block.category,
                version=block.version,
                requires=list(block.requires),
                produces=list(block.produces),
                default_config=dict(block.default_config),
                config_schema=dict(block.config_schema),
                ui_hints=dict(block.ui_hints),
                allowed_failure_policies=list(block.allowed_failure_policies),
                disabled_reason=block.disabled_reason,
            )
            for block in catalog.blocks
        ],
    )
