"""PDF rendering and OpenCV preprocessing adapter."""

import asyncio
from collections.abc import Callable
from concurrent.futures import Executor, ThreadPoolExecutor
from importlib import import_module
from io import BytesIO
from time import perf_counter
from typing import Any, Protocol, cast

from docmind_llmmagic.application.pipeline.steps.document_preprocessing.errors import (
    DocumentPreprocessingPageError,
    safe_preprocessing_error,
)
from docmind_llmmagic.application.pipeline.steps.document_preprocessing.ports import (
    PreparedPageContent,
    TransformedPageContent,
)
from docmind_llmmagic.application.pipeline.steps.document_preprocessing.validation import (
    validate_dimensions,
)
from docmind_llmmagic.domain.pipeline.errors import PipelineStepError
from docmind_llmmagic.domain.pipeline.preflight import PreparedPageFormat
from docmind_llmmagic.domain.pipeline.preprocessing import (
    ImagePreprocessingConfig,
    SourcePdfDocumentContent,
    TransformedPdfDocumentContent,
)
from docmind_llmmagic.infrastructure.pipeline.preprocessing.opencv import (
    OpenCVPageImageTransformer,
)

_PDF_POINTS_PER_INCH = 72.0
_MAX_PDF_TRANSFORM_WORKERS = 1
_PDF_TRANSFORM_EXECUTOR = ThreadPoolExecutor(
    max_workers=_MAX_PDF_TRANSFORM_WORKERS,
    thread_name_prefix="docmind-pdf-preprocessing",
)


class _PdfiumBitmap(Protocol):
    width: int
    height: int

    def to_numpy(self) -> Any: ...

    def close(self) -> None: ...


class _PdfiumPage(Protocol):
    def get_size(self) -> tuple[float, float]: ...

    def render(
        self,
        *,
        scale: float,
        grayscale: bool,
        fill_color: tuple[int, int, int, int],
        optimize_mode: str,
        rev_byteorder: bool,
    ) -> _PdfiumBitmap: ...

    def close(self) -> None: ...


class _PdfiumDocument(Protocol):
    def __len__(self) -> int: ...

    def __getitem__(self, index: int) -> _PdfiumPage: ...

    def close(self) -> None: ...


class OpenCVPdfDocumentTransformer:
    """Render a PDF at the configured DPI, preprocess each page, and rebuild a PDF."""

    def __init__(
        self,
        *,
        executor: Executor | None = None,
        page_transformer: OpenCVPageImageTransformer | None = None,
        clock: Callable[[], float] = perf_counter,
    ) -> None:
        self._executor = executor or _PDF_TRANSFORM_EXECUTOR
        self._page_transformer = page_transformer or OpenCVPageImageTransformer(
            executor=self._executor
        )
        self._clock = clock
        self._open_pdf = cast(
            Callable[[bytes], _PdfiumDocument],
            import_module("pypdfium2").PdfDocument,
        )
        self._reportlab_canvas = cast(Any, import_module("reportlab.pdfgen.canvas"))
        self._reportlab_utils = cast(Any, import_module("reportlab.lib.utils"))

    async def transform_document(
        self,
        document: SourcePdfDocumentContent,
        config: ImagePreprocessingConfig,
        *,
        deadline: float,
    ) -> TransformedPdfDocumentContent:
        """Run the CPU-bound PDF transformation outside the async request loop."""

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            self._executor,
            self._transform_document_sync,
            document,
            config,
            deadline,
        )

    def _transform_document_sync(
        self,
        document: SourcePdfDocumentContent,
        config: ImagePreprocessingConfig,
        deadline: float,
    ) -> TransformedPdfDocumentContent:
        source_pdf: _PdfiumDocument | None = None
        try:
            self._ensure_before_deadline(deadline)
            source_pdf = self._open_pdf(document.content)
            page_count = len(source_pdf)
            if page_count < 1:
                raise safe_preprocessing_error(
                    code="PREPROCESSING_PDF_EMPTY",
                    message="Document preprocessing requires at least one PDF page.",
                )
            if page_count > config.max_pages:
                raise safe_preprocessing_error(
                    code="PREPROCESSING_PDF_TOO_MANY_PAGES",
                    message="Document preprocessing PDF exceeds the page limit.",
                )

            output = BytesIO()
            canvas = self._reportlab_canvas.Canvas(
                output,
                pagesize=(1.0, 1.0),
                pageCompression=1,
                invariant=1,
            )
            operation_codes = ["PREPROCESSING_PDF_RENDERED", "PREPROCESSING_PDF_REBUILT"]
            warning_codes: list[str] = []
            for page_index in range(page_count):
                self._ensure_before_deadline(deadline)
                page = source_pdf[page_index]
                try:
                    width_points, height_points = page.get_size()
                    transformed_page = self._transform_page(
                        page=page,
                        page_number=page_index + 1,
                        source_reference=document.storage_reference,
                        width_points=float(width_points),
                        height_points=float(height_points),
                        config=config,
                    )
                    self._ensure_before_deadline(deadline)
                    canvas.setPageSize((float(width_points), float(height_points)))
                    canvas.drawImage(
                        self._reportlab_utils.ImageReader(BytesIO(transformed_page.content)),
                        0,
                        0,
                        width=float(width_points),
                        height=float(height_points),
                        preserveAspectRatio=False,
                        mask="auto",
                    )
                    canvas.showPage()
                    _extend_unique(
                        operation_codes,
                        transformed_page.transformation.operation_codes,
                    )
                    _extend_unique(
                        warning_codes,
                        transformed_page.transformation.warning_codes,
                    )
                finally:
                    page.close()

            self._ensure_before_deadline(deadline)
            canvas.save()
            return TransformedPdfDocumentContent(
                content=output.getvalue(),
                page_count=page_count,
                dpi=config.target_dpi,
                operation_codes=tuple(operation_codes),
                warning_codes=tuple(warning_codes),
            )
        except PipelineStepError:
            raise
        except DocumentPreprocessingPageError as exc:
            raise safe_preprocessing_error(
                code=exc.error_code,
                message="PDF page preprocessing failed.",
            ) from exc
        except Exception as exc:
            raise safe_preprocessing_error(
                code="PREPROCESSING_PDF_TRANSFORM_FAILED",
                message="PDF preprocessing failed.",
            ) from exc
        finally:
            if source_pdf is not None:
                source_pdf.close()

    def _ensure_before_deadline(self, deadline: float) -> None:
        if self._clock() >= deadline:
            raise safe_preprocessing_error(
                code="PREPROCESSING_PROCESSING_TIMEOUT",
                message="Document preprocessing exceeded the configured processing limit.",
            )

    def _transform_page(
        self,
        *,
        page: _PdfiumPage,
        page_number: int,
        source_reference: str,
        width_points: float,
        height_points: float,
        config: ImagePreprocessingConfig,
    ) -> TransformedPageContent:
        scale = config.target_dpi / _PDF_POINTS_PER_INCH
        validate_dimensions(
            width_px=max(1, round(width_points * scale)),
            height_px=max(1, round(height_points * scale)),
            config=config,
            error_code="PREPROCESSING_INPUT_PAGE_TOO_LARGE",
        )
        bitmap = page.render(
            scale=scale,
            grayscale=False,
            fill_color=(255, 255, 255, 255),
            optimize_mode="print",
            rev_byteorder=False,
        )
        try:
            prepared = PreparedPageContent(
                page_number=page_number,
                storage_reference=source_reference,
                content=b"",
                width_px=int(bitmap.width),
                height_px=int(bitmap.height),
                format=PreparedPageFormat.PNG,
                dpi=config.target_dpi,
            )
            return self._page_transformer.transform_decoded_page(
                page=prepared,
                image=bitmap.to_numpy(),
                config=config,
            )
        finally:
            bitmap.close()


def _extend_unique(target: list[str], values: tuple[str, ...]) -> None:
    for value in values:
        if value not in target:
            target.append(value)
