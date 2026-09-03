"""Internal OCR execution dependency wiring."""

from typing import Annotated

from fastapi import Depends, Request

from docmind_backend_runtime import create_dapr_client
from docmind_llmmagic.application.pipeline.invocation.async_execution import (
    AsyncOcrExecutionService,
    InMemoryOcrRunRegistry,
)
from docmind_llmmagic.application.pipeline.invocation.service import PipelineInvocationService
from docmind_llmmagic.bootstrap.dependencies.pipeline import get_pipeline_invocation_service
from docmind_llmmagic.infrastructure.ocr_pipeline_events.publisher import OcrPipelineEventPublisher
from docmind_llmmagic.settings import get_ocr_event_dapr_client_settings, get_ocr_max_concurrency


def get_async_ocr_execution_service(
    request: Request,
    invocation_service: Annotated[
        PipelineInvocationService, Depends(get_pipeline_invocation_service)
    ],
) -> AsyncOcrExecutionService:
    """Return the app-scoped bounded async OCR executor."""

    service = getattr(request.app.state, "async_ocr_execution", None)
    if (
        isinstance(service, AsyncOcrExecutionService)
        and service.invocation_service is invocation_service
    ):
        return service
    return build_async_ocr_execution_service(invocation_service)


def build_async_ocr_execution_service(
    invocation_service: object,
) -> AsyncOcrExecutionService:
    """Build the in-memory MVP executor for one LLM Magic replica."""

    if not isinstance(invocation_service, PipelineInvocationService):
        raise TypeError("A pipeline invocation service is required.")
    publisher = OcrPipelineEventPublisher(
        client_factory=lambda: create_dapr_client(get_ocr_event_dapr_client_settings()),
    )
    return AsyncOcrExecutionService(
        invocation_service,
        InMemoryOcrRunRegistry(max_concurrency=get_ocr_max_concurrency()),
        progress_publisher=publisher.progress,
        completion_publisher=publisher.completion,
        terminal_publisher=publisher.terminal,
        cancellation_publisher=publisher.cancelled,
    )
