"""Azure Blob storage adapter for preprocessed PDF documents."""

import asyncio
import hashlib
from collections.abc import Callable, Iterator
from pathlib import PurePosixPath
from typing import Protocol, cast
from urllib.parse import quote, unquote, urlsplit

from docmind_llmmagic.application.pipeline.steps.document_preprocessing.errors import (
    safe_preprocessing_error,
)
from docmind_llmmagic.domain.pipeline.errors import PipelineStepError
from docmind_llmmagic.domain.pipeline.preprocessing import (
    SourcePdfDocumentContent,
    StoredPreprocessedDocumentArtifact,
    TransformedPdfDocumentContent,
)

_ARTIFACT_VERSION = "preprocessed-pdf-v1"
_PDF_MEDIA_TYPE = "application/pdf"


class AzureBlobDownloadStream(Protocol):
    """Subset of the Azure download stream used by preprocessing."""

    def chunks(self) -> Iterator[bytes]: ...


class AzureBlobClient(Protocol):
    """Subset of Azure Blob client operations used by preprocessing."""

    def download_blob(self, *, timeout: float | None = None) -> AzureBlobDownloadStream: ...

    def upload_blob(
        self,
        data: bytes,
        *,
        overwrite: bool,
        content_settings: object | None = None,
        timeout: float | None = None,
    ) -> object: ...


class AzureBlobServiceClient(Protocol):
    """Subset of Azure Blob service operations used by preprocessing."""

    def get_blob_client(self, *, container: str, blob: str) -> AzureBlobClient: ...

    def close(self) -> None: ...


class AzureBlobPdfDocumentStorage:
    """Read source PDFs and write normalized PDFs beside the original blob."""

    def __init__(
        self,
        *,
        service_client: AzureBlobServiceClient,
        account_url: str | None,
        allowed_container_name: str,
        allowed_blob_prefix: str,
        operation_timeout_seconds: float,
        credential: object | None = None,
        content_settings_factory: Callable[[str], object | None] | None = None,
    ) -> None:
        self._service_client = service_client
        self._account_hostname = urlsplit(account_url or "").hostname
        self._allowed_container_name = _validated_container_name(allowed_container_name)
        self._allowed_blob_prefix = _validated_blob_prefix(allowed_blob_prefix)
        self._operation_timeout_seconds = operation_timeout_seconds
        self._credential = credential
        self._content_settings_factory = content_settings_factory or _content_settings

    async def read_document(
        self,
        storage_reference: str,
        *,
        max_bytes: int,
    ) -> SourcePdfDocumentContent:
        """Download one source PDF from a safe Azure Blob reference."""

        try:
            container_name, blob_name = _parse_storage_reference(
                storage_reference,
                expected_account_hostname=self._account_hostname,
                allowed_container_name=self._allowed_container_name,
                allowed_blob_prefix=self._allowed_blob_prefix,
            )
            blob_client = self._service_client.get_blob_client(
                container=container_name,
                blob=blob_name,
            )
            download = await asyncio.to_thread(
                blob_client.download_blob,
                timeout=self._operation_timeout_seconds,
            )
            content = await asyncio.to_thread(_read_bounded, download, max_bytes=max_bytes)
        except PipelineStepError:
            raise
        except Exception as exc:
            raise safe_preprocessing_error(
                code="PREPROCESSING_SOURCE_READ_FAILED",
                message="Document preprocessing could not read the source PDF.",
            ) from exc

        return SourcePdfDocumentContent(
            storage_reference=storage_reference,
            content=content,
        )

    async def store_document(
        self,
        *,
        source_storage_reference: str,
        run_id: str,
        document: TransformedPdfDocumentContent,
    ) -> StoredPreprocessedDocumentArtifact:
        """Write a deterministic run-scoped PDF in the source blob directory."""

        try:
            container_name, source_blob_name = _parse_storage_reference(
                source_storage_reference,
                expected_account_hostname=self._account_hostname,
                allowed_container_name=self._allowed_container_name,
                allowed_blob_prefix=self._allowed_blob_prefix,
            )
            output_blob_name = _preprocessed_blob_name(source_blob_name, run_id=run_id)
            _validate_blob_scope(
                container_name,
                output_blob_name,
                allowed_container_name=self._allowed_container_name,
                allowed_blob_prefix=self._allowed_blob_prefix,
            )
            blob_client = self._service_client.get_blob_client(
                container=container_name,
                blob=output_blob_name,
            )
            await asyncio.to_thread(
                blob_client.upload_blob,
                document.content,
                overwrite=True,
                content_settings=self._content_settings_factory(_PDF_MEDIA_TYPE),
                timeout=self._operation_timeout_seconds,
            )
        except PipelineStepError:
            raise
        except Exception as exc:
            raise safe_preprocessing_error(
                code="PREPROCESSING_OUTPUT_WRITE_FAILED",
                message="Document preprocessing could not store the normalized PDF.",
            ) from exc

        return StoredPreprocessedDocumentArtifact(
            storage_reference=_azure_blob_reference(container_name, output_blob_name),
            size_bytes=len(document.content),
            checksum=f"sha256:{hashlib.sha256(document.content).hexdigest()}",
            artifact_version=_ARTIFACT_VERSION,
        )

    async def close(self) -> None:
        """Close the Azure SDK client and its owned credential."""

        await asyncio.to_thread(self._service_client.close)
        if self._credential is not None:
            close = getattr(self._credential, "close", None)
            if callable(close):
                await asyncio.to_thread(close)


def build_azure_blob_pdf_document_storage(
    *,
    account_url: str | None,
    connection_string: str | None,
    allowed_container_name: str,
    allowed_blob_prefix: str,
    operation_timeout_seconds: float,
) -> AzureBlobPdfDocumentStorage:
    """Build Azure Blob preprocessing storage with managed identity or a local secret."""

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
            raise safe_preprocessing_error(
                code="PREPROCESSING_RUNTIME_NOT_CONFIGURED",
                message="Document preprocessing storage is not configured.",
            )
        from azure.identity import DefaultAzureCredential

        credential = DefaultAzureCredential()
        service_client = BlobServiceClient(
            account_url=account_url,
            credential=credential,
            transport=transport,
        )

    return AzureBlobPdfDocumentStorage(
        service_client=cast(AzureBlobServiceClient, service_client),
        account_url=account_url,
        allowed_container_name=allowed_container_name,
        allowed_blob_prefix=allowed_blob_prefix,
        operation_timeout_seconds=operation_timeout_seconds,
        credential=credential,
    )


def _parse_storage_reference(
    value: str,
    *,
    expected_account_hostname: str | None,
    allowed_container_name: str,
    allowed_blob_prefix: str,
) -> tuple[str, str]:
    parsed = urlsplit(value)
    if parsed.scheme == "azblob" and parsed.netloc and parsed.path:
        container_name, blob_name = parsed.netloc, unquote(parsed.path.lstrip("/"))
        _validate_blob_scope(
            container_name,
            blob_name,
            allowed_container_name=allowed_container_name,
            allowed_blob_prefix=allowed_blob_prefix,
        )
        return container_name, blob_name
    if parsed.scheme == "https" and parsed.hostname and parsed.path:
        if expected_account_hostname is None or parsed.hostname != expected_account_hostname:
            raise _unsupported_reference()
        path_parts = unquote(parsed.path.lstrip("/")).split("/", 1)
        if len(path_parts) == 2 and all(path_parts):
            container_name, blob_name = path_parts
            _validate_blob_scope(
                container_name,
                blob_name,
                allowed_container_name=allowed_container_name,
                allowed_blob_prefix=allowed_blob_prefix,
            )
            return container_name, blob_name

    raise _unsupported_reference()


def _validated_container_name(value: str) -> str:
    normalized = value.strip().lower()
    if not normalized or "/" in normalized or "\\" in normalized:
        raise ValueError("Azure Blob preprocessing container scope is invalid.")
    return normalized


def _validated_blob_prefix(value: str) -> str:
    normalized = value.strip().strip("/")
    if not normalized:
        raise ValueError("Azure Blob preprocessing prefix scope is invalid.")
    _validate_blob_path(normalized)
    return normalized


def _validate_blob_scope(
    container_name: str,
    blob_name: str,
    *,
    allowed_container_name: str,
    allowed_blob_prefix: str,
) -> None:
    _validate_blob_path(blob_name)
    if container_name.lower() != allowed_container_name:
        raise _unsupported_reference()
    if not blob_name.startswith(f"{allowed_blob_prefix}/"):
        raise _unsupported_reference()


def _validate_blob_path(blob_name: str) -> None:
    if "\\" in blob_name:
        raise _unsupported_reference()
    parts = blob_name.split("/")
    if not parts or any(part in {"", ".", ".."} for part in parts):
        raise _unsupported_reference()


def _read_bounded(download: AzureBlobDownloadStream, *, max_bytes: int) -> bytes:
    content = bytearray()
    for chunk in download.chunks():
        if len(content) + len(chunk) > max_bytes:
            raise safe_preprocessing_error(
                code="PREPROCESSING_SOURCE_DOCUMENT_INVALID",
                message="Document preprocessing source PDF is invalid.",
            )
        content.extend(chunk)
    return bytes(content)


def _preprocessed_blob_name(source_blob_name: str, *, run_id: str) -> str:
    source_path = PurePosixPath(source_blob_name)
    run_hash = hashlib.sha256(run_id.encode()).hexdigest()[:12]
    output_name = f"{source_path.stem}.preprocessed.{run_hash}.pdf"
    if str(source_path.parent) == ".":
        return output_name
    return f"{source_path.parent.as_posix()}/{output_name}"


def _azure_blob_reference(container_name: str, blob_name: str) -> str:
    return f"azblob://{container_name}/{quote(blob_name, safe='/-_.')}"


def _unsupported_reference() -> PipelineStepError:
    return safe_preprocessing_error(
        code="PREPROCESSING_SOURCE_REFERENCE_UNSUPPORTED",
        message="Document preprocessing source reference is not supported.",
    )


def _content_settings(media_type: str) -> object:
    from azure.storage.blob import ContentSettings

    return ContentSettings(content_type=media_type)
