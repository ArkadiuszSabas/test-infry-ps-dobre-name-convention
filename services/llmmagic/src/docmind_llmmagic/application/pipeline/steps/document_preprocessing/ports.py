"""Application ports used by the document preprocessing pipeline step."""

from dataclasses import dataclass
from typing import Protocol

from docmind_llmmagic.domain.pipeline.preflight import PreflightPageArtifact, PreparedPageFormat
from docmind_llmmagic.domain.pipeline.preprocessing import (
    ImagePreprocessingConfig,
    ImageTransformationMetadata,
    SourcePdfDocumentContent,
    StoredPreprocessedDocumentArtifact,
    StoredPreprocessedPageArtifact,
    TransformedPdfDocumentContent,
)


@dataclass(frozen=True, slots=True)
class PreparedPageContent:
    """Prepared page image bytes read from an internal artifact store."""

    page_number: int
    storage_reference: str
    content: bytes
    width_px: int | None
    height_px: int | None
    format: PreparedPageFormat
    dpi: int | None


@dataclass(frozen=True, slots=True)
class TransformedPageContent:
    """Transformed page image bytes ready to persist as a new artifact."""

    page_number: int
    content: bytes
    width_px: int
    height_px: int
    format: PreparedPageFormat
    dpi: int | None
    transformation: ImageTransformationMetadata


class PreparedPageArtifactReader(Protocol):
    """Read prepared page content from a safe preflight storage reference."""

    async def read_page(self, page: PreflightPageArtifact) -> PreparedPageContent: ...


class PageImageTransformer(Protocol):
    """Apply deterministic image preprocessing to one prepared page."""

    async def transform_page(
        self,
        page: PreparedPageContent,
        config: ImagePreprocessingConfig,
    ) -> TransformedPageContent: ...


class PreprocessedPageArtifactStore(Protocol):
    """Persist preprocessed page content and return safe storage metadata."""

    async def store_page(
        self,
        *,
        document_reference: str,
        run_id: str,
        page: TransformedPageContent,
    ) -> StoredPreprocessedPageArtifact: ...


class PdfDocumentArtifactStorage(Protocol):
    """Read source PDFs and persist normalized PDFs beside their source blob."""

    async def read_document(
        self,
        storage_reference: str,
        *,
        max_bytes: int,
    ) -> SourcePdfDocumentContent: ...

    async def store_document(
        self,
        *,
        source_storage_reference: str,
        run_id: str,
        document: TransformedPdfDocumentContent,
    ) -> StoredPreprocessedDocumentArtifact: ...


class PdfDocumentTransformer(Protocol):
    """Render and transform a PDF into a provider-ready normalized PDF."""

    async def transform_document(
        self,
        document: SourcePdfDocumentContent,
        config: ImagePreprocessingConfig,
        *,
        deadline: float,
    ) -> TransformedPdfDocumentContent: ...
