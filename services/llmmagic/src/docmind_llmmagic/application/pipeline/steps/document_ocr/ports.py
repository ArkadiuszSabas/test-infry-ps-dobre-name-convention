"""Application ports used by the document OCR/parsing pipeline step."""

from dataclasses import dataclass
from typing import Protocol

from docmind_llmmagic.domain.pipeline.ocr import (
    OcrParsingConfig,
    OcrProviderDocumentResult,
    OcrProviderPageResult,
)
from docmind_llmmagic.domain.pipeline.preflight import PreparedPageFormat
from docmind_llmmagic.domain.pipeline.preprocessing import PreprocessedPageArtifact


@dataclass(frozen=True, slots=True)
class OcrPageContent:
    """Preprocessed page image bytes read from an internal artifact store."""

    page_number: int
    storage_reference: str
    content: bytes
    width_px: int | None
    height_px: int | None
    format: PreparedPageFormat
    dpi: int | None


@dataclass(frozen=True, slots=True)
class OcrDocumentContent:
    """Source document reference prepared for provider-level OCR."""

    storage_reference: str
    provider_url: str
    media_type: str
    size_bytes: int


class OcrPageArtifactReader(Protocol):
    """Read preprocessed page content from a safe storage reference."""

    async def read_page(self, page: PreprocessedPageArtifact) -> OcrPageContent: ...


class OcrDocumentReferenceResolver(Protocol):
    """Resolve safe storage references to provider-readable document URLs."""

    def resolve_provider_url(self, storage_reference: str) -> str: ...


class DocumentOcrProvider(Protocol):
    """Analyze one preprocessed page through the configured OCR provider."""

    async def analyze_page(
        self,
        page: OcrPageContent,
        config: OcrParsingConfig,
    ) -> OcrProviderPageResult: ...


class DocumentReferenceOcrProvider(Protocol):
    """Analyze one source document reference through the configured OCR provider."""

    async def analyze_document(
        self,
        document: OcrDocumentContent,
        config: OcrParsingConfig,
    ) -> OcrProviderDocumentResult: ...
