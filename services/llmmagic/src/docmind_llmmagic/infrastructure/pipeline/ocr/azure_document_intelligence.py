"""Azure Document Intelligence OCR/parsing provider adapter."""

from collections.abc import Sequence
from importlib import import_module
from typing import Any, Protocol, cast

from docmind_llmmagic.application.pipeline.steps.document_ocr.errors import (
    safe_ocr_page_error,
)
from docmind_llmmagic.application.pipeline.steps.document_ocr.ports import (
    OcrDocumentContent,
    OcrPageContent,
)
from docmind_llmmagic.domain.pipeline.ocr import (
    OcrKeyValuePair,
    OcrParsingConfig,
    OcrProviderDocumentResult,
    OcrProviderPageResult,
    OcrTextLine,
    OcrTextWord,
)
from docmind_llmmagic.domain.pipeline.preflight import PreparedPageFormat
from docmind_llmmagic.infrastructure.pipeline.ocr.azure_document_intelligence_layout import (
    document_page_text,
    map_selection_marks,
    map_tables,
)

_PNG_CONTENT_TYPE = "image/png"
_JPEG_CONTENT_TYPE = "image/jpeg"
_TIFF_CONTENT_TYPE = "image/tiff"


class _AnalyzePoller(Protocol):
    async def result(self) -> object: ...


class _DocumentIntelligenceClient(Protocol):
    async def begin_analyze_document(
        self,
        model_id: str,
        body: object,
        *,
        content_type: str | None = None,
        connection_timeout: float,
        read_timeout: float,
        features: Sequence[object] | None = None,
    ) -> _AnalyzePoller: ...

    async def close(self) -> None: ...


class AzureDocumentIntelligenceProvider:
    """Analyze preprocessed page artifacts with Azure Document Intelligence."""

    def __init__(self, *, client: _DocumentIntelligenceClient) -> None:
        self._client = client

    async def close(self) -> None:
        """Release the underlying asynchronous Azure SDK transport."""

        await self._client.close()

    async def analyze_page(
        self,
        page: OcrPageContent,
        config: OcrParsingConfig,
    ) -> OcrProviderPageResult:
        """Submit one page to Azure DI and map the response to safe domain contracts."""

        try:
            content_type = _content_type(page.format)
            if config.include_key_value_pairs:
                poller = await self._client.begin_analyze_document(
                    config.model_id,
                    page.content,
                    content_type=content_type,
                    connection_timeout=config.request_timeout_seconds,
                    read_timeout=config.request_timeout_seconds,
                    features=_key_value_pair_features(),
                )
            else:
                poller = await self._client.begin_analyze_document(
                    config.model_id,
                    page.content,
                    content_type=content_type,
                    connection_timeout=config.request_timeout_seconds,
                    read_timeout=config.request_timeout_seconds,
                )
            result = await poller.result()
        except Exception as exc:
            raise safe_ocr_page_error(_provider_error_code(exc)) from exc

        return _map_result(result=result, source_page=page, config=config)

    async def analyze_document(
        self,
        document: OcrDocumentContent,
        config: OcrParsingConfig,
    ) -> OcrProviderDocumentResult:
        """Submit one source document URL to Azure DI and map safe OCR results."""

        try:
            request = _analyze_document_request(document.provider_url)
            if config.include_key_value_pairs:
                poller = await self._client.begin_analyze_document(
                    config.model_id,
                    request,
                    connection_timeout=config.request_timeout_seconds,
                    read_timeout=config.request_timeout_seconds,
                    features=_key_value_pair_features(),
                )
            else:
                poller = await self._client.begin_analyze_document(
                    config.model_id,
                    request,
                    connection_timeout=config.request_timeout_seconds,
                    read_timeout=config.request_timeout_seconds,
                )
            result = await poller.result()
        except Exception as exc:
            raise safe_ocr_page_error(_provider_error_code(exc)) from exc

        return _map_document_result(result=result, document=document, config=config)


def build_azure_document_intelligence_provider(
    *,
    endpoint: str,
    managed_identity_client_id: str | None = None,
    api_version: str | None = None,
) -> AzureDocumentIntelligenceProvider:
    """Build an Azure DI provider from runtime settings."""

    if not endpoint:
        raise ValueError("Azure Document Intelligence endpoint is required.")

    document_module = import_module("azure.ai.documentintelligence.aio")
    client_class: Any = document_module.__dict__["DocumentIntelligenceClient"]

    client_kwargs: dict[str, object] = {
        "endpoint": endpoint,
        "credential": _build_credential(managed_identity_client_id=managed_identity_client_id),
    }
    if api_version:
        client_kwargs["api_version"] = api_version

    client: _DocumentIntelligenceClient = client_class(**client_kwargs)
    return AzureDocumentIntelligenceProvider(client=client)


def _build_credential(*, managed_identity_client_id: str | None) -> object:
    identity_module = import_module("azure.identity.aio")
    if managed_identity_client_id:
        credential_class: Any = identity_module.__dict__["ManagedIdentityCredential"]
        return credential_class(client_id=managed_identity_client_id)

    credential_class = identity_module.__dict__["DefaultAzureCredential"]
    return credential_class()


def _content_type(page_format: PreparedPageFormat) -> str:
    if page_format == PreparedPageFormat.PNG:
        return _PNG_CONTENT_TYPE

    format_value = str(page_format).lower()
    if format_value in {"jpeg", "jpg"}:
        return _JPEG_CONTENT_TYPE
    if format_value in {"tif", "tiff"}:
        return _TIFF_CONTENT_TYPE

    return _PNG_CONTENT_TYPE


def _map_result(
    *,
    result: object,
    source_page: OcrPageContent,
    config: OcrParsingConfig,
) -> OcrProviderPageResult:
    pages = _object_sequence(getattr(result, "pages", ()))
    provider_page = pages[0] if pages else None
    lines = _lines(provider_page)
    words = _words(provider_page)
    text = _result_text(result=result, lines=lines)
    warning_codes = _warning_codes(text=text, page_count=len(pages))
    key_value_pairs = (
        _key_value_pairs(result=result, source_page_number=source_page.page_number)
        if config.include_key_value_pairs
        else ()
    )
    selection_marks = (
        map_selection_marks(provider_page, page_number=source_page.page_number)
        if config.include_selection_marks
        else ()
    )
    tables = (
        map_tables(
            result,
            table_id_prefix=f"page-{source_page.page_number}",
            page_number_override=source_page.page_number,
        )
        if config.include_tables
        else ()
    )

    return OcrProviderPageResult(
        page_number=source_page.page_number,
        text=text,
        lines=lines,
        words=words if config.include_word_details else (),
        width_px=_int_attr(provider_page, "width") or source_page.width_px,
        height_px=_int_attr(provider_page, "height") or source_page.height_px,
        format=source_page.format,
        dpi=source_page.dpi,
        confidence=_average_confidence(words),
        warning_codes=warning_codes,
        provider_page_count=len(pages) or 1,
        key_value_pairs=key_value_pairs,
        selection_marks=selection_marks,
        tables=tables,
        coordinate_width=_float_attr(provider_page, "width")
        or _positive_float(source_page.width_px),
        coordinate_height=_float_attr(provider_page, "height")
        or _positive_float(source_page.height_px),
    )


def _key_value_pair_features() -> tuple[object, ...]:
    models_module = import_module("azure.ai.documentintelligence.models")
    document_analysis_feature = models_module.__dict__["DocumentAnalysisFeature"]
    return (document_analysis_feature.KEY_VALUE_PAIRS,)


def _analyze_document_request(url: str) -> object:
    models_module = import_module("azure.ai.documentintelligence.models")
    request_class: Any = models_module.__dict__["AnalyzeDocumentRequest"]
    return request_class(url_source=url)


def _map_document_result(
    *,
    result: object,
    document: OcrDocumentContent,
    config: OcrParsingConfig,
) -> OcrProviderDocumentResult:
    del document
    provider_pages = _object_sequence(getattr(result, "pages", ()))
    key_value_pairs = (
        _key_value_pairs(result=result, source_page_number=1)
        if config.include_key_value_pairs
        else ()
    )
    tables = map_tables(result, table_id_prefix="document") if config.include_tables else ()
    pages: list[OcrProviderPageResult] = []
    for index, provider_page in enumerate(provider_pages or (None,), start=1):
        lines = _lines(provider_page)
        words = _words(provider_page)
        text = document_page_text(
            result=result,
            page=provider_page,
            lines=lines,
            page_count=len(provider_pages) or 1,
        )
        pages.append(
            OcrProviderPageResult(
                page_number=index,
                text=text,
                lines=lines,
                words=words if config.include_word_details else (),
                width_px=_int_attr(provider_page, "width"),
                height_px=_int_attr(provider_page, "height"),
                format=None,
                dpi=None,
                confidence=_average_confidence(words),
                warning_codes=_warning_codes(text=text, page_count=len(provider_pages) or 1),
                provider_page_count=len(provider_pages) or 1,
                key_value_pairs=tuple(
                    pair for pair in key_value_pairs if pair.page_number == index
                ),
                selection_marks=(
                    map_selection_marks(provider_page, page_number=index)
                    if config.include_selection_marks
                    else ()
                ),
                coordinate_width=_float_attr(provider_page, "width"),
                coordinate_height=_float_attr(provider_page, "height"),
            )
        )

    return OcrProviderDocumentResult(
        pages=tuple(pages),
        key_value_pairs=key_value_pairs,
        tables=tables,
        provider_page_count=len(provider_pages) or len(pages),
    )


def _key_value_pairs(
    *,
    result: object,
    source_page_number: int,
) -> tuple[OcrKeyValuePair, ...]:
    values: list[tuple[int, float, float, int, str, str, float | None, tuple[float, ...]]] = []
    raw_pairs = _object_sequence(getattr(result, "key_value_pairs", ()))
    for source_index, pair in enumerate(raw_pairs, start=1):
        key = _content(getattr(pair, "key", None))
        value = _content(getattr(pair, "value", None))
        if not key and not value:
            continue

        page_number, top, left, polygon = _element_anchor(
            getattr(pair, "key", None),
            fallback_page_number=source_page_number,
        )
        if not polygon:
            value_page_number, value_top, value_left, value_polygon = _element_anchor(
                getattr(pair, "value", None),
                fallback_page_number=source_page_number,
            )
            page_number = value_page_number
            top = value_top
            left = value_left
            polygon = value_polygon

        values.append(
            (
                page_number,
                top,
                left,
                source_index,
                key,
                value,
                _confidence(getattr(pair, "confidence", None)),
                polygon,
            )
        )

    values.sort(key=lambda item: (item[0], item[1], item[2], item[3]))
    return tuple(
        OcrKeyValuePair(
            key=key,
            value=value,
            confidence=confidence,
            page_number=page_number,
            source="azure_document_intelligence",
            bounding_polygon=polygon,
            order_index=order_index,
        )
        for order_index, (
            page_number,
            _top,
            _left,
            _source_index,
            key,
            value,
            confidence,
            polygon,
        ) in enumerate(values, start=1)
    )


def _content(value: object | None) -> str:
    content = getattr(value, "content", None)
    return content if isinstance(content, str) else ""


def _element_anchor(
    value: object | None,
    *,
    fallback_page_number: int,
) -> tuple[int, float, float, tuple[float, ...]]:
    for region in _object_sequence(getattr(value, "bounding_regions", ())):
        page_number = _positive_int(getattr(region, "page_number", None)) or fallback_page_number
        polygon = _polygon(getattr(region, "polygon", ()))
        top, left = _polygon_top_left(polygon)
        return page_number, top, left, polygon

    return fallback_page_number, float("inf"), float("inf"), ()


def _lines(page: object | None) -> tuple[OcrTextLine, ...]:
    if page is None:
        return ()

    values: list[OcrTextLine] = []
    for line in _object_sequence(getattr(page, "lines", ())):
        content = getattr(line, "content", None)
        if isinstance(content, str):
            values.append(
                OcrTextLine(
                    content=content,
                    bounding_polygon=_polygon(getattr(line, "polygon", ())),
                )
            )

    return tuple(values)


def _words(page: object | None) -> tuple[OcrTextWord, ...]:
    if page is None:
        return ()

    values: list[OcrTextWord] = []
    for word in _object_sequence(getattr(page, "words", ())):
        content = getattr(word, "content", None)
        if isinstance(content, str):
            values.append(
                OcrTextWord(
                    content=content,
                    confidence=_confidence(getattr(word, "confidence", None)),
                    bounding_polygon=_polygon(getattr(word, "polygon", ())),
                )
            )

    return tuple(values)


def _result_text(*, result: object, lines: tuple[OcrTextLine, ...]) -> str:
    content = getattr(result, "content", None)
    if isinstance(content, str):
        return content

    return "\n".join(line.content for line in lines)


def _warning_codes(*, text: str, page_count: int) -> tuple[str, ...]:
    warnings: list[str] = []
    if not text.strip():
        warnings.append("OCR_NO_TEXT_DETECTED")
    if page_count > 1:
        warnings.append("OCR_PROVIDER_RETURNED_MULTIPLE_PAGES")

    return tuple(warnings)


def _average_confidence(words: tuple[OcrTextWord, ...]) -> float | None:
    values = [word.confidence for word in words if word.confidence is not None]
    if not values:
        return None

    return round(sum(values) / len(values), 6)


def _confidence(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None

    return max(0.0, min(1.0, float(value)))


def _int_attr(value: object | None, name: str) -> int | None:
    raw_value = getattr(value, name, None)
    return _positive_int(raw_value)


def _float_attr(value: object | None, name: str) -> float | None:
    raw_value = getattr(value, name, None)
    return _positive_float(raw_value)


def _positive_float(raw_value: object) -> float | None:
    if isinstance(raw_value, bool) or not isinstance(raw_value, int | float):
        return None
    result = float(raw_value)
    return result if result > 0 else None


def _positive_int(raw_value: object) -> int | None:
    if isinstance(raw_value, bool) or not isinstance(raw_value, int | float):
        return None

    int_value = round(float(raw_value))
    return int_value if int_value > 0 else None


def _polygon(value: object) -> tuple[float, ...]:
    if not isinstance(value, Sequence) or isinstance(value, str | bytes):
        return ()

    sequence = cast(Sequence[object], value)
    coordinates: list[float] = []
    for item in sequence:
        if isinstance(item, bool):
            return ()
        if isinstance(item, int | float):
            coordinates.append(round(float(item), 4))
            continue

        point_x = getattr(item, "x", None)
        point_y = getattr(item, "y", None)
        if isinstance(point_x, int | float) and isinstance(point_y, int | float):
            coordinates.extend((round(float(point_x), 4), round(float(point_y), 4)))
            continue

        return ()

    return tuple(coordinates)


def _polygon_top_left(polygon: tuple[float, ...]) -> tuple[float, float]:
    if len(polygon) < 2 or len(polygon) % 2 != 0:
        return float("inf"), float("inf")

    x_coordinates = polygon[0::2]
    y_coordinates = polygon[1::2]
    return min(y_coordinates), min(x_coordinates)


def _object_sequence(value: object) -> tuple[object, ...]:
    if not isinstance(value, Sequence) or isinstance(value, str | bytes):
        return ()

    sequence = cast(Sequence[object], value)
    return tuple(sequence)


def _provider_error_code(exc: Exception) -> str:
    status_code = getattr(exc, "status_code", None)
    if status_code == 400:
        return "OCR_PROVIDER_BAD_REQUEST"
    if status_code in {401, 403}:
        return "OCR_PROVIDER_AUTH_FAILED"
    if status_code == 408:
        return "OCR_PROVIDER_TIMEOUT"
    if status_code == 429:
        return "OCR_PROVIDER_RATE_LIMITED"
    if isinstance(status_code, int) and status_code >= 500:
        return "OCR_PROVIDER_UNAVAILABLE"

    class_name = exc.__class__.__name__
    if class_name in {"ClientAuthenticationError"}:
        return "OCR_PROVIDER_AUTH_FAILED"
    if class_name in {"ServiceRequestError", "ServiceResponseError"}:
        return "OCR_PROVIDER_UNAVAILABLE"

    return "OCR_PROVIDER_REQUEST_FAILED"
