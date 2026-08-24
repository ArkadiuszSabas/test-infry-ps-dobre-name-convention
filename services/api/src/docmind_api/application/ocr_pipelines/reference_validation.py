"""Reference validation diagnostics for OCR pipeline definitions."""

from docmind_api.application.ocr_pipelines.diagnostics import error_diagnostic
from docmind_api.application.ocr_pipelines.ports import (
    AttributeDefinitionReferenceCatalog,
    DocumentTypeReferenceCatalog,
)
from docmind_api.application.ocr_pipelines.references import (
    REFERENCE_VALIDATED_IMPLEMENTATION_IDS,
    attribute_references,
    document_type_reference,
)
from docmind_api.domain.attributes.models import AttributeStatus
from docmind_api.domain.document_types.models import DocumentTypeStatus
from docmind_api.domain.ocr_pipelines.models import (
    OcrPipelineDiagnostic,
    OcrPipelineDraftDefinition,
    OcrPipelineStepDefinition,
)


async def reference_diagnostics(
    *,
    definition: OcrPipelineDraftDefinition,
    document_type_reference_catalog: DocumentTypeReferenceCatalog | None,
    attribute_reference_catalog: AttributeDefinitionReferenceCatalog | None,
) -> tuple[OcrPipelineDiagnostic, ...]:
    """Return catalog-reference diagnostics for one OCR pipeline definition."""

    diagnostics: list[OcrPipelineDiagnostic] = []
    for step_index, step in enumerate(definition.steps):
        if step.implementation_id not in REFERENCE_VALIDATED_IMPLEMENTATION_IDS:
            continue
        diagnostics.extend(
            await _step_reference_diagnostics(
                step=step,
                step_index=step_index,
                document_type_reference_catalog=document_type_reference_catalog,
                attribute_reference_catalog=attribute_reference_catalog,
            ),
        )
    return tuple(diagnostics)


async def _step_reference_diagnostics(
    *,
    step: OcrPipelineStepDefinition,
    step_index: int,
    document_type_reference_catalog: DocumentTypeReferenceCatalog | None,
    attribute_reference_catalog: AttributeDefinitionReferenceCatalog | None,
) -> tuple[OcrPipelineDiagnostic, ...]:
    diagnostics: list[OcrPipelineDiagnostic] = []
    config_path = f"steps[{step_index}].config"
    document_type = document_type_reference(step.config)
    if document_type is not None:
        diagnostics.extend(
            await _document_type_diagnostics(
                reference=document_type,
                step_id=step.step_id,
                path=config_path,
                document_type_reference_catalog=document_type_reference_catalog,
            ),
        )
    for attribute in attribute_references(step.config, path=config_path):
        diagnostics.extend(
            await _attribute_diagnostics(
                reference=attribute.value,
                step_id=step.step_id,
                path=attribute.path,
                attribute_reference_catalog=attribute_reference_catalog,
            ),
        )
    return tuple(diagnostics)


async def _document_type_diagnostics(
    *,
    reference: str,
    step_id: str,
    path: str,
    document_type_reference_catalog: DocumentTypeReferenceCatalog | None,
) -> tuple[OcrPipelineDiagnostic, ...]:
    if document_type_reference_catalog is None:
        return (_reference_unavailable(path=path, step_id=step_id),)
    document_type = await document_type_reference_catalog.get_by_id(reference)
    if document_type is None:
        document_type = await document_type_reference_catalog.get_by_external_id(reference)
    if document_type is None:
        return (
            error_diagnostic(
                "UNKNOWN_DOCUMENT_TYPE_REFERENCE",
                "OCR pipeline step references an unknown document type.",
                path=path,
                step_id=step_id,
            ),
        )
    if document_type.status != DocumentTypeStatus.ACTIVE:
        return (
            error_diagnostic(
                "INACTIVE_DOCUMENT_TYPE_REFERENCE",
                "OCR pipeline step references an inactive document type.",
                path=path,
                step_id=step_id,
            ),
        )
    return ()


async def _attribute_diagnostics(
    *,
    reference: str,
    step_id: str,
    path: str,
    attribute_reference_catalog: AttributeDefinitionReferenceCatalog | None,
) -> tuple[OcrPipelineDiagnostic, ...]:
    if attribute_reference_catalog is None:
        return (_reference_unavailable(path=path, step_id=step_id),)
    attribute = await attribute_reference_catalog.get_by_id(reference)
    if attribute is None:
        attribute = await attribute_reference_catalog.get_by_external_id(reference)
    if attribute is None:
        return (
            error_diagnostic(
                "UNKNOWN_ATTRIBUTE_REFERENCE",
                "OCR pipeline step references an unknown attribute definition.",
                path=path,
                step_id=step_id,
            ),
        )
    if attribute.status != AttributeStatus.ACTIVE:
        return (
            error_diagnostic(
                "INACTIVE_ATTRIBUTE_REFERENCE",
                "OCR pipeline step references an inactive attribute definition.",
                path=path,
                step_id=step_id,
            ),
        )
    return ()


def _reference_unavailable(*, path: str, step_id: str) -> OcrPipelineDiagnostic:
    return error_diagnostic(
        "REFERENCE_VALIDATION_UNAVAILABLE",
        "Catalog reference validation is unavailable.",
        path=path,
        step_id=step_id,
    )
