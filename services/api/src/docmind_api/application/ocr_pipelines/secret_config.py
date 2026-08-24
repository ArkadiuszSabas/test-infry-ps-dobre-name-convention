"""Secret-field diagnostics for OCR pipeline step config."""

from docmind_api.application.ocr_pipelines.diagnostics import error_diagnostic
from docmind_api.application.ocr_pipelines.json_helpers import object_mapping, object_sequence
from docmind_api.domain.ocr_pipelines.models import (
    OcrPipelineDiagnostic,
    OcrPipelineStepDefinition,
)

_SECRET_KEY_MARKERS = frozenset(
    {
        "api_key",
        "apikey",
        "connection_string",
        "credential",
        "password",
        "secret",
        "subscription_key",
        "token",
    },
)


def secret_config_diagnostics(
    *,
    step: OcrPipelineStepDefinition,
    step_index: int,
) -> tuple[OcrPipelineDiagnostic, ...]:
    """Return diagnostics for secret-looking UI config keys."""

    return tuple(
        secret_diagnostics_for_value(
            value=step.config,
            path=f"steps[{step_index}].config",
            step_id=step.step_id,
        ),
    )


def secret_diagnostics_for_value(
    *,
    value: object,
    path: str,
    step_id: str,
) -> tuple[OcrPipelineDiagnostic, ...]:
    """Recursively inspect config keys for secret-looking names."""

    diagnostics: list[OcrPipelineDiagnostic] = []
    mapping_value = object_mapping(value)
    if mapping_value is not None:
        for key, child in mapping_value.items():
            key_text = str(key)
            child_path = f"{path}.{key_text}"
            normalized_key = key_text.lower().replace("-", "_")
            if any(marker in normalized_key for marker in _SECRET_KEY_MARKERS):
                diagnostics.append(
                    error_diagnostic(
                        "SECRET_CONFIG_FIELD_REJECTED",
                        "OCR pipeline UI config cannot contain secrets or credentials.",
                        path=child_path,
                        step_id=step_id,
                    ),
                )
            diagnostics.extend(
                secret_diagnostics_for_value(
                    value=child,
                    path=child_path,
                    step_id=step_id,
                ),
            )
        return tuple(diagnostics)

    array_value = object_sequence(value)
    if array_value is None:
        return tuple(diagnostics)
    for index, child in enumerate(array_value):
        diagnostics.extend(
            secret_diagnostics_for_value(
                value=child,
                path=f"{path}[{index}]",
                step_id=step_id,
            ),
        )
    return tuple(diagnostics)
