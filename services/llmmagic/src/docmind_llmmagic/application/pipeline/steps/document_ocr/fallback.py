"""Fallback OCR/Vision decision helpers."""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field, replace
from time import perf_counter

from docmind_llmmagic.application.pipeline.steps.document_ocr.artifacts import parsed_page
from docmind_llmmagic.application.pipeline.steps.document_ocr.errors import (
    DocumentOcrPageError,
    safe_ocr_page_error,
)
from docmind_llmmagic.application.pipeline.steps.document_ocr.fallback_policy import (
    FALLBACK_FAILED,
    FALLBACK_PROCESSING_TIMEOUT,
    FALLBACK_PROVIDER_UNAVAILABLE,
    fallback_reasons_for_provider_error,
    fallback_reasons_for_result,
    fallback_skip_reason,
)
from docmind_llmmagic.application.pipeline.steps.document_ocr.ports import (
    DocumentOcrProvider,
    OcrPageContent,
)
from docmind_llmmagic.application.pipeline.steps.document_ocr.validation import (
    failed_page,
    validate_provider_result,
)
from docmind_llmmagic.domain.pipeline.ocr import (
    OcrFallbackConfig,
    OcrFallbackStatus,
    OcrPageArtifact,
    OcrParsingConfig,
)
from docmind_llmmagic.domain.pipeline.preflight import DocumentInputKind
from docmind_llmmagic.domain.pipeline.preprocessing import PreprocessedPageArtifact

_LOGGER = logging.getLogger(__name__)


def _empty_reason_codes() -> set[str]:
    return set()


@dataclass(slots=True)
class OcrFallbackOutcomeTracker:
    """Track safe aggregate fallback outcomes for OCR trace metrics."""

    configured: bool
    triggered_page_count: int = 0
    attempted_page_count: int = 0
    succeeded_page_count: int = 0
    failed_page_count: int = 0
    warning_page_count: int = 0
    skipped_page_count: int = 0
    _started_at: float | None = field(default=None, init=False, repr=False)
    _reason_codes: set[str] = field(
        default_factory=_empty_reason_codes,
        init=False,
        repr=False,
    )

    @property
    def started_at(self) -> float:
        """Return the first fallback attempt start time, setting it when needed."""

        if self._started_at is None:
            self._started_at = perf_counter()

        return self._started_at

    def trigger(self, reason_codes: tuple[str, ...]) -> None:
        """Record a page-level fallback trigger."""

        self.triggered_page_count += 1
        self._reason_codes.update(reason_codes)

    def skip(self, reason_code: str) -> None:
        """Record a skipped fallback after a trigger."""

        self.skipped_page_count += 1
        self._reason_codes.add(reason_code)

    def start(self) -> None:
        """Record a fallback attempt."""

        self.attempted_page_count += 1

    def succeed(self) -> None:
        """Record a successful fallback attempt."""

        self.succeeded_page_count += 1

    def fail(self, reason_code: str) -> None:
        """Record a failed fallback attempt."""

        self.failed_page_count += 1
        self._reason_codes.add(reason_code)

    def warn(self, reason_code: str) -> None:
        """Record a recoverable fallback failure where primary output remains available."""

        self.warning_page_count += 1
        self._reason_codes.add(reason_code)

    @property
    def status(self) -> OcrFallbackStatus:
        """Return the aggregate fallback status."""

        if not self.configured:
            return OcrFallbackStatus.NOT_CONFIGURED
        if self.attempted_page_count == 0:
            return OcrFallbackStatus.SKIPPED
        if (
            self.failed_page_count == 0
            and self.warning_page_count == 0
            and self.skipped_page_count == 0
        ):
            return OcrFallbackStatus.SUCCEEDED
        if (
            self.succeeded_page_count == 0
            and self.warning_page_count == 0
            and self.skipped_page_count == 0
        ):
            return OcrFallbackStatus.FAILED

        return OcrFallbackStatus.WARNING

    @property
    def reason_codes(self) -> tuple[str, ...]:
        """Return sorted safe fallback reason codes."""

        return tuple(sorted(self._reason_codes))


def fallback_provider_config(config: OcrParsingConfig) -> OcrParsingConfig:
    """Build the provider config used for fallback OCR attempts."""

    fallback = config.fallback
    return replace(
        config,
        provider_id=fallback.provider_id,
        model_id=fallback.model_id,
        request_timeout_seconds=fallback.request_timeout_seconds,
        max_processing_seconds=fallback.max_processing_seconds,
        fallback=OcrFallbackConfig(),
    )


async def maybe_fallback_for_primary_result(
    *,
    fallback_provider: DocumentOcrProvider | None,
    page: OcrPageArtifact,
    page_content: OcrPageContent,
    source_page: PreprocessedPageArtifact,
    config: OcrParsingConfig,
    document_kind: DocumentInputKind | None,
    fallback_tracker: OcrFallbackOutcomeTracker,
) -> OcrPageArtifact:
    """Attempt fallback for a parsed primary page when explicit quality triggers match."""

    reason_codes = fallback_reasons_for_result(page=page, config=config)
    if not config.fallback.enabled or not reason_codes:
        return page

    return await _attempt_fallback(
        fallback_provider=fallback_provider,
        page_content=page_content,
        source_page=source_page,
        primary_page=page,
        primary_error_code=None,
        reason_codes=reason_codes,
        config=config,
        document_kind=document_kind,
        fallback_tracker=fallback_tracker,
    )


async def maybe_fallback_for_primary_error(
    *,
    fallback_provider: DocumentOcrProvider | None,
    error_code: str,
    page_content: OcrPageContent,
    source_page: PreprocessedPageArtifact,
    config: OcrParsingConfig,
    document_kind: DocumentInputKind | None,
    fallback_tracker: OcrFallbackOutcomeTracker,
) -> OcrPageArtifact:
    """Attempt fallback for a primary provider/page failure when triggers match."""

    reason_codes = fallback_reasons_for_provider_error(error_code=error_code, config=config)
    if not config.fallback.enabled or not reason_codes:
        return failed_page(page=source_page, config=config, error_code=error_code)

    return await _attempt_fallback(
        fallback_provider=fallback_provider,
        page_content=page_content,
        source_page=source_page,
        primary_page=None,
        primary_error_code=error_code,
        reason_codes=reason_codes,
        config=config,
        document_kind=document_kind,
        fallback_tracker=fallback_tracker,
    )


async def _attempt_fallback(
    *,
    fallback_provider: DocumentOcrProvider | None,
    page_content: OcrPageContent,
    source_page: PreprocessedPageArtifact,
    primary_page: OcrPageArtifact | None,
    primary_error_code: str | None,
    reason_codes: tuple[str, ...],
    config: OcrParsingConfig,
    document_kind: DocumentInputKind | None,
    fallback_tracker: OcrFallbackOutcomeTracker,
) -> OcrPageArtifact:
    fallback_tracker.trigger(reason_codes)
    skip_reason = fallback_skip_reason(
        config=config,
        document_kind=document_kind,
        fallback_provider_available=fallback_provider is not None,
        attempted_page_count=fallback_tracker.attempted_page_count,
    )
    if skip_reason is not None:
        fallback_tracker.skip(skip_reason)
        return _fallback_skipped_page(
            source_page=source_page,
            primary_page=primary_page,
            primary_error_code=primary_error_code,
            reason_codes=reason_codes,
            skip_reason=skip_reason,
            config=config,
        )

    fallback_config = fallback_provider_config(config)
    fallback_tracker.start()
    try:
        if fallback_provider is None:
            raise safe_ocr_page_error(FALLBACK_PROVIDER_UNAVAILABLE)
        provider_result = await _with_fallback_processing_timeout(
            lambda: fallback_provider.analyze_page(page_content, fallback_config),
            started_at=fallback_tracker.started_at,
            config=config,
        )
        validate_provider_result(
            provider_result,
            expected_page_number=source_page.page_number,
        )
    except DocumentOcrPageError as exc:
        return _fallback_failed_page(
            source_page=source_page,
            primary_page=primary_page,
            primary_error_code=primary_error_code,
            reason_codes=reason_codes,
            fallback_error_code=exc.error_code,
            fallback_config=fallback_config,
            fallback_tracker=fallback_tracker,
        )
    except Exception:
        _LOGGER.exception(
            "Unexpected fallback OCR provider failure.",
            extra={"page_number": source_page.page_number},
        )
        return _fallback_failed_page(
            source_page=source_page,
            primary_page=primary_page,
            primary_error_code=primary_error_code,
            reason_codes=reason_codes,
            fallback_error_code=FALLBACK_FAILED,
            fallback_config=fallback_config,
            fallback_tracker=fallback_tracker,
        )

    fallback_tracker.succeed()
    fallback_page = parsed_page(
        source_page=source_page,
        provider_result=provider_result,
        config=fallback_config,
    )
    return replace(
        fallback_page,
        selection_marks=(
            primary_page.selection_marks
            if primary_page is not None and primary_page.selection_marks
            else fallback_page.selection_marks
        ),
        fallback_used=True,
        fallback_reason_codes=reason_codes,
        primary_error_code=primary_error_code,
    )


async def _with_fallback_processing_timeout[T](
    operation: Callable[[], Awaitable[T]],
    *,
    started_at: float,
    config: OcrParsingConfig,
) -> T:
    remaining_seconds = config.fallback.max_processing_seconds - (perf_counter() - started_at)
    if remaining_seconds <= 0:
        raise safe_ocr_page_error(FALLBACK_PROCESSING_TIMEOUT)

    try:
        return await asyncio.wait_for(operation(), timeout=remaining_seconds)
    except TimeoutError as exc:
        raise safe_ocr_page_error(FALLBACK_PROCESSING_TIMEOUT) from exc


def _fallback_skipped_page(
    *,
    source_page: PreprocessedPageArtifact,
    primary_page: OcrPageArtifact | None,
    primary_error_code: str | None,
    reason_codes: tuple[str, ...],
    skip_reason: str,
    config: OcrParsingConfig,
) -> OcrPageArtifact:
    if primary_page is not None:
        return replace(
            primary_page,
            fallback_reason_codes=reason_codes,
            fallback_error_code=skip_reason,
        )

    page = failed_page(
        page=source_page,
        config=config,
        error_code=primary_error_code or "OCR_PAGE_FAILED",
    )
    return replace(
        page,
        fallback_reason_codes=reason_codes,
        fallback_error_code=skip_reason,
        primary_error_code=primary_error_code,
    )


def _fallback_failed_page(
    *,
    source_page: PreprocessedPageArtifact,
    primary_page: OcrPageArtifact | None,
    primary_error_code: str | None,
    reason_codes: tuple[str, ...],
    fallback_error_code: str,
    fallback_config: OcrParsingConfig,
    fallback_tracker: OcrFallbackOutcomeTracker,
) -> OcrPageArtifact:
    fallback_tracker.fail(fallback_error_code)
    if primary_page is not None:
        fallback_tracker.warn(fallback_error_code)
        return replace(
            primary_page,
            fallback_reason_codes=reason_codes,
            fallback_error_code=fallback_error_code,
            warning_codes=_append_warning_code(primary_page.warning_codes, FALLBACK_FAILED),
        )

    page = failed_page(page=source_page, config=fallback_config, error_code=fallback_error_code)
    return replace(
        page,
        fallback_reason_codes=reason_codes,
        fallback_error_code=fallback_error_code,
        primary_error_code=primary_error_code,
    )


def _append_warning_code(codes: tuple[str, ...], code: str) -> tuple[str, ...]:
    if code in codes:
        return codes

    return (*codes, code)
