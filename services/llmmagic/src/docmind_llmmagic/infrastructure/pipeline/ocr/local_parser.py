"""Local document parser OCR/parsing provider adapter."""

import asyncio
import re
from dataclasses import dataclass
from typing import Protocol

from docmind_llmmagic.application.pipeline.steps.document_ocr.errors import (
    DocumentOcrPageError,
    safe_ocr_page_error,
)
from docmind_llmmagic.application.pipeline.steps.document_ocr.ports import OcrPageContent
from docmind_llmmagic.domain.pipeline.ocr import (
    OcrParsingConfig,
    OcrProviderPageResult,
    OcrTextLine,
    OcrTextWord,
)
from docmind_llmmagic.domain.pipeline.preflight import PreparedPageFormat

_SAFE_ERROR_CODE_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]{1,79}$")


@dataclass(frozen=True, slots=True)
class LocalParserPageInput:
    """One preprocessed page submitted to a local parser implementation."""

    page_number: int
    content: bytes
    width_px: int | None
    height_px: int | None
    format: PreparedPageFormat
    dpi: int | None


@dataclass(frozen=True, slots=True)
class LocalParserPageResult:
    """Provider-neutral local parser result for one page."""

    page_number: int
    text: str
    lines: tuple[OcrTextLine, ...] = ()
    words: tuple[OcrTextWord, ...] = ()
    width_px: int | None = None
    height_px: int | None = None
    format: PreparedPageFormat | None = None
    dpi: int | None = None
    confidence: float | None = None
    warning_codes: tuple[str, ...] = ()
    provider_page_count: int = 1


class LocalPageParser(Protocol):
    """Local parser engine boundary used by the provider adapter."""

    async def parse_page(
        self,
        page: LocalParserPageInput,
        *,
        model_id: str,
        timeout_seconds: float,
    ) -> LocalParserPageResult: ...


class LocalParserPageError(Exception):
    """Safe local parser page failure."""

    def __init__(self, error_code: str) -> None:
        super().__init__("Local parser page analysis failed.")
        self.error_code = error_code


class LocalDocumentParserProvider:
    """Analyze preprocessed page artifacts with an injected local parser implementation."""

    def __init__(
        self,
        *,
        parser: LocalPageParser,
        supported_formats: tuple[PreparedPageFormat, ...] = (PreparedPageFormat.PNG,),
    ) -> None:
        self._parser = parser
        self._supported_formats = supported_formats

    async def analyze_page(
        self,
        page: OcrPageContent,
        config: OcrParsingConfig,
    ) -> OcrProviderPageResult:
        """Submit one prepared page to the local parser and map the safe result."""

        if page.format not in self._supported_formats:
            raise safe_ocr_page_error("OCR_PROVIDER_UNSUPPORTED_FORMAT")

        try:
            result = await asyncio.wait_for(
                self._parser.parse_page(
                    LocalParserPageInput(
                        page_number=page.page_number,
                        content=page.content,
                        width_px=page.width_px,
                        height_px=page.height_px,
                        format=page.format,
                        dpi=page.dpi,
                    ),
                    model_id=config.model_id,
                    timeout_seconds=config.request_timeout_seconds,
                ),
                timeout=config.request_timeout_seconds,
            )
        except DocumentOcrPageError:
            raise
        except LocalParserPageError as exc:
            raise safe_ocr_page_error(_local_parser_error_code(exc)) from exc
        except TimeoutError as exc:
            raise safe_ocr_page_error("OCR_PROVIDER_TIMEOUT") from exc
        except Exception as exc:
            raise safe_ocr_page_error(_unexpected_parser_error_code(exc)) from exc

        return _map_result(result=result, source_page=page)


def _map_result(
    *,
    result: LocalParserPageResult,
    source_page: OcrPageContent,
) -> OcrProviderPageResult:
    return OcrProviderPageResult(
        page_number=result.page_number,
        text=result.text,
        lines=result.lines,
        words=result.words,
        width_px=_positive_int_or_default(result.width_px, source_page.width_px),
        height_px=_positive_int_or_default(result.height_px, source_page.height_px),
        format=_format_or_default(result.format, source_page.format),
        dpi=_positive_int_or_default(result.dpi, source_page.dpi),
        confidence=result.confidence,
        warning_codes=result.warning_codes,
        provider_page_count=_positive_int_or_default(result.provider_page_count, 1) or 1,
    )


def _local_parser_error_code(exc: LocalParserPageError) -> str:
    error_code = exc.error_code
    if _SAFE_ERROR_CODE_PATTERN.fullmatch(error_code):
        return error_code

    return "OCR_PROVIDER_REQUEST_FAILED"


def _unexpected_parser_error_code(exc: Exception) -> str:
    class_name = exc.__class__.__name__
    if class_name in {"UnsupportedFormatError", "UnsupportedDocumentError"}:
        return "OCR_PROVIDER_UNSUPPORTED_FORMAT"

    return "OCR_PROVIDER_REQUEST_FAILED"


def _positive_int_or_default(value: object, default: int | None) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        return default

    return value


def _format_or_default(
    value: object,
    default: PreparedPageFormat,
) -> PreparedPageFormat:
    return value if isinstance(value, PreparedPageFormat) else default
