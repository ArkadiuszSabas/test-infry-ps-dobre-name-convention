"""Runtime adapters for OCR pipeline runs."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from docmind_api.application.ocr_pipeline_runs.ports import OcrPipelineRunInvocationContext
from docmind_api.domain.ocr_pipeline_runs.models import OcrPipelineRunRecord


class UtcClock:
    """UTC clock used for OCR pipeline run timestamps."""

    def now(self) -> datetime:
        """Return the current UTC timestamp."""

        return datetime.now(tz=UTC)


class UuidOcrPipelineRunIdFactory:
    """UUID4 id factory for OCR pipeline runs."""

    def new_id(self) -> UUID:
        """Return a new OCR pipeline run id."""

        return uuid4()


class UuidOcrPipelineRunExecutionIdentityFactory:
    """Distinct UUID4 identifiers for attempts and opaque ownership."""

    def new_attempt_id(self) -> UUID:
        """Return a physical execution attempt id."""

        return uuid4()

    def new_owner_token(self) -> UUID:
        """Return an opaque ownership token independent from run and attempt ids."""

        return uuid4()


class UnavailableOcrPipelineRunInvoker:
    """Placeholder invoker for request-scoped services that do not execute runs."""

    async def invoke_run(
        self,
        record: OcrPipelineRunRecord,
        context: OcrPipelineRunInvocationContext,
    ) -> OcrPipelineRunRecord:
        """Fail closed if a request-scoped service is accidentally used for execution."""

        del record, context
        from docmind_api.application.ocr_pipeline_runs.errors import (
            OcrPipelineRunLlmMagicUnavailableError,
        )

        raise OcrPipelineRunLlmMagicUnavailableError()
