"""Config-schema diagnostics for OCR pipeline step config."""

from collections.abc import Mapping

from docmind_api.application.ocr_pipelines.diagnostics import error_diagnostic
from docmind_api.application.ocr_pipelines.json_helpers import (
    object_mapping,
    object_sequence,
    schema_mapping,
)
from docmind_api.domain.ocr_pipelines.models import (
    OcrPipelineBlockMetadata,
    OcrPipelineDiagnostic,
    OcrPipelineStepDefinition,
)


def config_schema_diagnostics(
    *,
    block: OcrPipelineBlockMetadata,
    step: OcrPipelineStepDefinition,
    step_index: int,
) -> tuple[OcrPipelineDiagnostic, ...]:
    """Return diagnostics for config fields unsupported by the block contract."""

    if not block.config_schema:
        return ()
    return tuple(
        _config_value_diagnostics(
            value=step.config,
            schema=block.config_schema,
            path=f"steps[{step_index}].config",
            step_id=step.step_id,
        ),
    )


def _config_value_diagnostics(
    *,
    value: object,
    schema: Mapping[str, object],
    path: str,
    step_id: str,
) -> tuple[OcrPipelineDiagnostic, ...]:
    options = _schema_options(schema)
    if options:
        option_results = tuple(
            _config_value_diagnostics(
                value=value,
                schema=option,
                path=path,
                step_id=step_id,
            )
            for option in options
        )
        if any(not diagnostics for diagnostics in option_results):
            return ()
        return (_config_value_invalid(path=path, step_id=step_id),)

    expected_type = schema.get("type")
    if isinstance(expected_type, str) and not _matches_schema_type(value, expected_type):
        return (_config_value_invalid(path=path, step_id=step_id),)

    enum_values = object_sequence(schema.get("enum"))
    if enum_values is not None and value not in enum_values:
        return (_config_value_invalid(path=path, step_id=step_id),)

    if _schema_type_includes(schema, "object") or "properties" in schema:
        object_value = object_mapping(value)
        if object_value is None:
            return (_config_value_invalid(path=path, step_id=step_id),)
        return _object_config_diagnostics(
            value=object_value,
            schema=schema,
            path=path,
            step_id=step_id,
        )

    if _schema_type_includes(schema, "array"):
        return _array_config_diagnostics(
            value=value,
            schema=schema,
            path=path,
            step_id=step_id,
        )
    return ()


def _array_config_diagnostics(
    *,
    value: object,
    schema: Mapping[str, object],
    path: str,
    step_id: str,
) -> tuple[OcrPipelineDiagnostic, ...]:
    array_value = object_sequence(value)
    if array_value is None:
        return (_config_value_invalid(path=path, step_id=step_id),)
    max_items = schema.get("maxItems")
    if (
        isinstance(max_items, int)
        and not isinstance(max_items, bool)
        and len(array_value) > max_items
    ):
        return (_config_value_invalid(path=path, step_id=step_id),)
    item_schema = schema_mapping(schema.get("items"))
    if item_schema is None:
        return ()

    diagnostics: list[OcrPipelineDiagnostic] = []
    for index, child in enumerate(array_value):
        diagnostics.extend(
            _config_value_diagnostics(
                value=child,
                schema=item_schema,
                path=f"{path}[{index}]",
                step_id=step_id,
            ),
        )
    return tuple(diagnostics)


def _object_config_diagnostics(
    *,
    value: Mapping[object, object],
    schema: Mapping[str, object],
    path: str,
    step_id: str,
) -> tuple[OcrPipelineDiagnostic, ...]:
    properties = schema_mapping(schema.get("properties")) or {}
    additional_allowed = schema.get("additionalProperties") is not False
    diagnostics: list[OcrPipelineDiagnostic] = []
    for key, child in value.items():
        key_text = str(key)
        child_path = f"{path}.{key_text}"
        child_schema = schema_mapping(properties.get(key_text))
        if child_schema is None:
            if not additional_allowed:
                diagnostics.append(
                    error_diagnostic(
                        "CONFIG_FIELD_NOT_ALLOWED",
                        "OCR pipeline step config contains a field outside the block contract.",
                        path=child_path,
                        step_id=step_id,
                    ),
                )
            continue
        diagnostics.extend(
            _config_value_diagnostics(
                value=child,
                schema=child_schema,
                path=child_path,
                step_id=step_id,
            ),
        )
    return tuple(diagnostics)


def _schema_options(schema: Mapping[str, object]) -> tuple[Mapping[str, object], ...]:
    for key in ("oneOf", "anyOf"):
        options = object_sequence(schema.get(key))
        if options is None:
            continue
        schemas: list[Mapping[str, object]] = []
        for option in options:
            schema_option = schema_mapping(option)
            if schema_option is not None:
                schemas.append(schema_option)
        return tuple(schemas)
    return ()


def _schema_type_includes(schema: Mapping[str, object], expected_type: str) -> bool:
    configured_type = schema.get("type")
    if isinstance(configured_type, str):
        return configured_type == expected_type
    configured_types = object_sequence(configured_type)
    if configured_types is not None:
        return expected_type in configured_types
    return False


def _matches_schema_type(value: object, expected_type: str) -> bool:
    if expected_type == "object":
        return isinstance(value, Mapping)
    if expected_type == "array":
        return isinstance(value, list | tuple)
    if expected_type == "string":
        return isinstance(value, str)
    if expected_type == "boolean":
        return isinstance(value, bool)
    if expected_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected_type == "number":
        return isinstance(value, int | float) and not isinstance(value, bool)
    return True


def _config_value_invalid(*, path: str, step_id: str) -> OcrPipelineDiagnostic:
    return error_diagnostic(
        "CONFIG_VALUE_INVALID",
        "OCR pipeline step config value does not match the block schema.",
        path=path,
        step_id=step_id,
    )
