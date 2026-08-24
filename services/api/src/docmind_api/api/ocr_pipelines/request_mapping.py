"""Request-to-command mapping helpers for OCR pipeline routes."""

from docmind_api.api.ocr_pipelines.schemas import (
    OcrPipelineStepRequest,
    UpdateOcrPipelineDraftRequest,
)
from docmind_api.application.ocr_pipelines.commands import (
    PRESERVE_OCR_PIPELINE_DRAFT_FIELD,
    OcrPipelineDescriptionUpdate,
    OcrPipelineNameUpdate,
    OcrPipelineStepsUpdate,
)
from docmind_api.application.ocr_pipelines.errors import OcrPipelineValidationError
from docmind_api.domain.ocr_pipelines.models import OcrPipelineStepDefinition


def name_update_from_request(
    request: UpdateOcrPipelineDraftRequest,
) -> OcrPipelineNameUpdate:
    """Return a command-safe name update value."""

    if "name" not in request.model_fields_set:
        return PRESERVE_OCR_PIPELINE_DRAFT_FIELD
    if request.name is None:
        raise OcrPipelineValidationError(message="OCR pipeline name cannot be null.")
    return request.name


def description_update_from_request(
    request: UpdateOcrPipelineDraftRequest,
) -> OcrPipelineDescriptionUpdate:
    """Return a command-safe description update value."""

    if "description" not in request.model_fields_set:
        return PRESERVE_OCR_PIPELINE_DRAFT_FIELD
    return request.description


def steps_update_from_request(
    request: UpdateOcrPipelineDraftRequest,
) -> OcrPipelineStepsUpdate:
    """Return a command-safe ordered step update value."""

    if "steps" not in request.model_fields_set:
        return PRESERVE_OCR_PIPELINE_DRAFT_FIELD
    if request.steps is None:
        raise OcrPipelineValidationError(message="OCR pipeline steps cannot be null.")
    return steps_from_request(request.steps)


def steps_from_request(
    requests: list[OcrPipelineStepRequest],
) -> tuple[OcrPipelineStepDefinition, ...]:
    """Map HTTP step payloads to application/domain step definitions."""

    try:
        return tuple(
            OcrPipelineStepDefinition(
                step_id=request.step_id,
                implementation_id=request.implementation_id,
                display_name=request.display_name,
                enabled=request.enabled,
                failure_policy=request.failure_policy,
                config=request.config,
            )
            for request in requests
        )
    except ValueError as error:
        raise OcrPipelineValidationError(message=str(error)) from error
