"""Compiled OCR pipeline snapshot helpers for run initialization."""

from collections.abc import Mapping, Sequence
from typing import Any, cast

from docmind_api.domain.ocr_pipeline_runs.constants import OCR_PIPELINE_RUN_MAX_STEP_COUNT
from docmind_api.domain.ocr_pipeline_runs.value_objects import OcrPipelineRunStep


def pending_steps_from_compiled_snapshot(
    compiled_snapshot: Mapping[str, Any],
    *,
    max_step_count: int = OCR_PIPELINE_RUN_MAX_STEP_COUNT,
) -> tuple[OcrPipelineRunStep, ...]:
    """Create pending step records from an LLM Magic compiled definition snapshot."""

    raw_steps = compiled_snapshot.get("steps")
    if not isinstance(raw_steps, Sequence) or isinstance(raw_steps, str | bytes):
        raise ValueError("Compiled OCR pipeline snapshot must contain a steps array.")
    steps = tuple(cast(Sequence[object], raw_steps))
    if len(steps) < 1:
        raise ValueError("Compiled OCR pipeline snapshot must contain at least one step.")
    if len(steps) > max_step_count:
        raise ValueError("Compiled OCR pipeline snapshot exceeds the run step limit.")

    return tuple(_step_from_compiled_snapshot(step) for step in steps)


def _step_from_compiled_snapshot(value: object) -> OcrPipelineRunStep:
    if not isinstance(value, Mapping):
        raise ValueError("Compiled OCR pipeline step must be a JSON object.")
    mapping = cast(Mapping[object, object], value)
    return OcrPipelineRunStep(
        step_id=_required_mapping_text(mapping, "step_id"),
        step_type=_required_mapping_text(mapping, "step_type"),
        implementation_id=_required_mapping_text(mapping, "implementation_id"),
        display_name=_required_mapping_text(mapping, "display_name"),
    )


def _required_mapping_text(mapping: Mapping[object, object], key: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str):
        raise ValueError(f"Compiled OCR pipeline step {key} is required.")
    return value
