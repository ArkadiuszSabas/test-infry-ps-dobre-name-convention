"""Mutable OCR pipeline run persistence values."""

from docmind_api.domain.ocr_pipeline_runs.models import OcrPipelineRunRecord
from docmind_api.infrastructure.persistence.ocr_pipeline_runs.mappers import record_to_values


def mutable_run_values(record: OcrPipelineRunRecord) -> dict[str, object]:
    values = record_to_values(record)
    mutable_names = {
        "status",
        "steps",
        "metrics",
        "diagnostics",
        "error",
        "result_payload",
        "updated_at",
        "started_at",
        "completed_at",
    }
    return {name: value for name, value in values.items() if name in mutable_names}
