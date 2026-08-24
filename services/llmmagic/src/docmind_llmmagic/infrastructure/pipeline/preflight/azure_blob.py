"""Azure Blob backed PDF metadata provider for document preflight."""

import asyncio
import hashlib
import re
from collections.abc import Iterator
from typing import Protocol, cast
from urllib.parse import quote, unquote, urlsplit

from docmind_llmmagic.application.pipeline.steps.document_preflight.errors import (
    safe_preflight_error,
)
from docmind_llmmagic.domain.pipeline.errors import PipelineStepError
from docmind_llmmagic.domain.pipeline.models import MetricValue
from docmind_llmmagic.domain.pipeline.preflight import DocumentInputDescriptor, PreflightLimits
from docmind_llmmagic.infrastructure.pipeline.preflight.pdf import (
    PdfInspection,
    PdfiumPdfInspector,
)

_PDF_MEDIA_TYPE = "application/pdf"
_SAFE_CONTAINER_SEGMENT_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_SAFE_BLOB_SEGMENT_PATTERN = re.compile(
    r"^(?:[A-Za-z0-9]|%[0-9A-Fa-f]{2})"
    r"(?:[A-Za-z0-9._-]|%[0-9A-Fa-f]{2}){0,127}$"
)


class AzureBlobDownloadStream(Protocol):
    """Subset of the Azure download stream used by preflight."""

    def chunks(self) -> Iterator[bytes]: ...


class AzureBlobProperties(Protocol):
    """Subset of Azure Blob properties required before download."""

    @property
    def size(self) -> object: ...


class AzureBlobClient(Protocol):
    """Subset of Azure Blob client operations used by preflight."""

    def get_blob_properties(self, *, timeout: float | None = None) -> AzureBlobProperties: ...

    def download_blob(self, *, timeout: float | None = None) -> AzureBlobDownloadStream: ...


class AzureBlobServiceClient(Protocol):
    """Subset of Azure Blob service operations used by preflight."""

    def get_blob_client(self, *, container: str, blob: str) -> AzureBlobClient: ...

    def close(self) -> None: ...


class PdfInspector(Protocol):
    """Inspect one complete PDF payload without rendering it."""

    def inspect(self, content: bytes) -> PdfInspection: ...


class AzureBlobPdfDocumentMetadataProvider:
    """Download and structurally validate one original PDF blob."""

    def __init__(
        self,
        *,
        service_client: AzureBlobServiceClient,
        account_url: str | None,
        operation_timeout_seconds: float,
        inspector: PdfInspector | None = None,
        credential: object | None = None,
    ) -> None:
        self._service_client = service_client
        self._account_hostname = urlsplit(account_url or "").hostname
        self._operation_timeout_seconds = operation_timeout_seconds
        self._inspector = inspector or PdfiumPdfInspector()
        self._credential = credential

    async def get_descriptor(
        self,
        document_reference: str,
        limits: PreflightLimits,
        metadata: dict[str, MetricValue] | None = None,
    ) -> DocumentInputDescriptor:
        """Read the complete bounded blob and return validated PDF metadata."""

        del metadata
        try:
            container_name, blob_name = _parse_storage_reference(
                document_reference,
                expected_account_hostname=self._account_hostname,
            )
            blob_client = self._service_client.get_blob_client(
                container=container_name,
                blob=blob_name,
            )
            properties = await asyncio.to_thread(
                blob_client.get_blob_properties,
                timeout=self._operation_timeout_seconds,
            )
            expected_size = _validated_blob_size(properties)
            if expected_size > limits.max_document_bytes:
                raise safe_preflight_error(
                    code="PREFLIGHT_DOCUMENT_TOO_LARGE",
                    message="Document exceeds the configured size limit.",
                )
            download = await asyncio.to_thread(
                blob_client.download_blob,
                timeout=self._operation_timeout_seconds,
            )
            content = await asyncio.to_thread(
                _read_bounded,
                download,
                max_bytes=limits.max_document_bytes,
            )
            if len(content) != expected_size:
                raise safe_preflight_error(
                    code="PREFLIGHT_SOURCE_READ_FAILED",
                    message="Document preflight could not read the complete source PDF.",
                )
            inspection = await asyncio.to_thread(self._inspector.inspect, content)
        except PipelineStepError:
            raise
        except Exception as exc:
            raise safe_preflight_error(
                code="PREFLIGHT_SOURCE_READ_FAILED",
                message="Document preflight could not read the source PDF.",
            ) from exc

        return DocumentInputDescriptor(
            document_reference=document_reference,
            media_type=_PDF_MEDIA_TYPE,
            size_bytes=len(content),
            file_extension="pdf",
            declared_page_count=inspection.page_count,
            source_storage_reference=_canonical_reference(container_name, blob_name),
            content_checksum=f"sha256:{hashlib.sha256(content).hexdigest()}",
            diagnostic_codes=(
                "PREFLIGHT_SOURCE_BLOB_VALIDATED",
                "PREFLIGHT_PDF_STRUCTURE_VALIDATED",
            ),
        )

    async def close(self) -> None:
        """Close the Azure SDK client and its owned credential."""

        await asyncio.to_thread(self._service_client.close)
        if self._credential is not None:
            close = getattr(self._credential, "close", None)
            if callable(close):
                await asyncio.to_thread(close)


class UnconfiguredDocumentMetadataProvider:
    """Fail closed when source Azure Blob access is not configured."""

    async def get_descriptor(
        self,
        document_reference: str,
        limits: PreflightLimits,
        metadata: dict[str, MetricValue] | None = None,
    ) -> DocumentInputDescriptor:
        del document_reference, limits, metadata
        raise safe_preflight_error(
            code="PREFLIGHT_RUNTIME_NOT_CONFIGURED",
            message="Document preflight storage is not configured.",
        )


def build_azure_blob_pdf_document_metadata_provider(
    *,
    account_url: str | None,
    connection_string: str | None,
    operation_timeout_seconds: float,
) -> AzureBlobPdfDocumentMetadataProvider:
    """Build Azure Blob preflight access with managed identity or a local secret."""

    from azure.core.pipeline.transport import RequestsTransport
    from azure.storage.blob import BlobServiceClient

    transport = RequestsTransport(
        connection_timeout=operation_timeout_seconds,
        read_timeout=operation_timeout_seconds,
    )
    credential: object | None = None
    if connection_string is not None:
        service_client = BlobServiceClient.from_connection_string(
            connection_string,
            transport=transport,
        )
    else:
        if account_url is None:
            raise safe_preflight_error(
                code="PREFLIGHT_RUNTIME_NOT_CONFIGURED",
                message="Document preflight storage is not configured.",
            )
        from azure.identity import DefaultAzureCredential

        credential = DefaultAzureCredential()
        service_client = BlobServiceClient(
            account_url=account_url,
            credential=credential,
            transport=transport,
        )

    return AzureBlobPdfDocumentMetadataProvider(
        service_client=cast(AzureBlobServiceClient, service_client),
        account_url=account_url,
        operation_timeout_seconds=operation_timeout_seconds,
        credential=credential,
    )


def _parse_storage_reference(
    value: str,
    *,
    expected_account_hostname: str | None,
) -> tuple[str, str]:
    if not value or "\\" in value:
        raise _unsupported_reference()
    parsed = urlsplit(value)
    if (
        parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise _unsupported_reference()

    if parsed.scheme == "azblob" and parsed.netloc and parsed.path:
        container_name = parsed.netloc
        blob_name = unquote(parsed.path.lstrip("/"))
    elif parsed.scheme == "https" and parsed.hostname and parsed.path:
        if expected_account_hostname is None or parsed.hostname != expected_account_hostname:
            raise _unsupported_reference()
        path_parts = unquote(parsed.path.lstrip("/")).split("/", 1)
        if len(path_parts) != 2:
            raise _unsupported_reference()
        container_name, blob_name = path_parts
    else:
        raise _unsupported_reference()

    if not _is_safe_container_segment(container_name):
        raise _unsupported_reference()
    blob_segments = blob_name.split("/")
    if not blob_segments or not all(_is_safe_blob_segment(segment) for segment in blob_segments):
        raise _unsupported_reference()
    return container_name, blob_name


def _validated_blob_size(properties: AzureBlobProperties) -> int:
    size: object = properties.size
    if isinstance(size, bool) or not isinstance(size, int) or size < 1:
        raise safe_preflight_error(
            code="PREFLIGHT_SOURCE_METADATA_INVALID",
            message="Document preflight source metadata is invalid.",
        )
    return size


def _read_bounded(download: AzureBlobDownloadStream, *, max_bytes: int) -> bytes:
    content = bytearray()
    for chunk in download.chunks():
        if len(content) + len(chunk) > max_bytes:
            raise safe_preflight_error(
                code="PREFLIGHT_DOCUMENT_TOO_LARGE",
                message="Document exceeds the configured size limit.",
            )
        content.extend(chunk)
    return bytes(content)


def _canonical_reference(container_name: str, blob_name: str) -> str:
    return f"azblob://{container_name}/{quote(blob_name, safe='/-_.')}"


def _is_safe_container_segment(value: str) -> bool:
    return value not in {".", ".."} and _SAFE_CONTAINER_SEGMENT_PATTERN.fullmatch(value) is not None


def _is_safe_blob_segment(value: str) -> bool:
    return value not in {".", ".."} and _SAFE_BLOB_SEGMENT_PATTERN.fullmatch(value) is not None


def _unsupported_reference() -> PipelineStepError:
    return safe_preflight_error(
        code="PREFLIGHT_SOURCE_REFERENCE_UNSUPPORTED",
        message="Document source reference is not supported for OCR preflight.",
    )
