"""Application ports used by the document preflight pipeline step."""

from collections.abc import Sequence
from typing import Protocol

from docmind_llmmagic.domain.pipeline.models import MetricValue
from docmind_llmmagic.domain.pipeline.preflight import (
    DocumentInputDescriptor,
    PagePreparationOutcome,
    PreflightLimits,
    PreparedPageCandidate,
    StoredPageArtifact,
)


class DocumentMetadataProvider(Protocol):
    """Resolve safe metadata for a document reference."""

    async def get_descriptor(
        self,
        document_reference: str,
        limits: PreflightLimits,
        metadata: dict[str, MetricValue] | None = None,
    ) -> DocumentInputDescriptor: ...


class DocumentPagePreparer(Protocol):
    """Render or prepare source documents into page candidates."""

    async def prepare_pdf_pages(
        self,
        descriptor: DocumentInputDescriptor,
        limits: PreflightLimits,
    ) -> Sequence[PagePreparationOutcome]: ...

    async def prepare_image_page(
        self,
        descriptor: DocumentInputDescriptor,
        limits: PreflightLimits,
    ) -> PagePreparationOutcome: ...


class PreparedPageArtifactStore(Protocol):
    """Persist prepared page artifacts and return safe storage references."""

    async def store_page(
        self,
        *,
        document_reference: str,
        run_id: str,
        page: PreparedPageCandidate,
    ) -> StoredPageArtifact: ...
