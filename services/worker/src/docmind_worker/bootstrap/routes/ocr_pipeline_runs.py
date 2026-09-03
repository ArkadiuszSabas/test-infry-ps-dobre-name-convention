"""Route registration for Worker OCR run dispatch."""

from fastapi import APIRouter

from docmind_worker.api.ocr_pipeline_runs.router import create_ocr_pipeline_run_router
from docmind_worker.bootstrap.dependencies.ocr_pipeline_runs import (
    build_ocr_run_cancellation_consumer_dependency,
    build_ocr_run_dispatch_consumer_dependency,
)


def get_ocr_pipeline_run_router(*, include_smoke_subscription: bool) -> APIRouter:
    """Return the Worker OCR run Dapr router."""

    return create_ocr_pipeline_run_router(
        consumer_dependency=build_ocr_run_dispatch_consumer_dependency(),
        cancellation_consumer_dependency=build_ocr_run_cancellation_consumer_dependency(),
        include_smoke_subscription=include_smoke_subscription,
    )
