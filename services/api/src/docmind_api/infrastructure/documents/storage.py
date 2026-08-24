"""Document content storage adapters."""

import asyncio
from collections.abc import Callable
from pathlib import Path, PurePath
from typing import Protocol, cast
from urllib.parse import quote, unquote, urlsplit

from docmind_api.application.documents.ports import (
    DocumentContentStorage,
    DocumentContentStorageError,
    DocumentContentStorageNotFoundError,
    StoredDocumentContent,
    StoreDocumentContentCommand,
)
from docmind_api.domain.documents.models import StorageLocator

_AZURE_BLOB_LOCATOR_SCHEME = "azblob"


class FilesystemDocumentContentStorage(DocumentContentStorage):
    """Store raw document content in a local filesystem directory."""

    def __init__(self, root_path: Path) -> None:
        self._root_path = root_path

    async def save(self, command: StoreDocumentContentCommand) -> StorageLocator:
        """Persist content and return a file URI locator."""

        try:
            path = await asyncio.to_thread(self._write_file, command)
        except OSError as error:
            raise DocumentContentStorageError(str(error)) from error

        return StorageLocator(path.resolve().as_uri())

    async def delete(self, locator: StorageLocator) -> None:
        """Delete previously stored content when ingest compensation is needed."""

        try:
            await asyncio.to_thread(self._delete_file, locator)
        except (OSError, ValueError) as error:
            raise DocumentContentStorageError(str(error)) from error

    async def load(self, locator: StorageLocator) -> StoredDocumentContent:
        """Load stored content from a file URI locator."""

        try:
            content = await asyncio.to_thread(self._read_file, locator)
        except FileNotFoundError as error:
            raise DocumentContentStorageNotFoundError(str(error)) from error
        except (OSError, ValueError) as error:
            raise DocumentContentStorageError(str(error)) from error

        return StoredDocumentContent(content=content)

    def _write_file(self, command: StoreDocumentContentCommand) -> Path:
        document_dir = self._root_path / str(command.document_id)
        document_dir.mkdir(parents=True, exist_ok=True)
        path = document_dir / _safe_filename(command.original_filename)
        with path.open("xb") as file:
            file.write(command.content)
        return path

    def _delete_file(self, locator: StorageLocator) -> None:
        path = self._path_from_locator(locator)
        path.unlink(missing_ok=True)
        try:
            path.parent.rmdir()
        except OSError:
            return

    def _read_file(self, locator: StorageLocator) -> bytes:
        return self._path_from_locator(locator).read_bytes()

    def _path_from_locator(self, locator: StorageLocator) -> Path:
        path = Path.from_uri(locator.value).resolve()
        root_path = self._root_path.resolve()
        if not path.is_relative_to(root_path):
            raise DocumentContentStorageError("Storage locator is outside configured root.")

        return path


def _safe_filename(value: str) -> str:
    filename = PurePath(value).name.strip()
    if not filename:
        return "document.bin"

    safe_characters = [
        character if character.isalnum() or character in {".", "-", "_"} else "_"
        for character in filename
    ]
    sanitized = "".join(safe_characters).strip("._")
    return sanitized or "document.bin"


class AzureBlobClientFactory(Protocol):
    """Factory for Azure Blob container clients."""

    def container_client(self) -> AzureBlobContainerClient: ...

    def close(self) -> None: ...


class AzureBlobServiceClient(Protocol):
    """Subset of Azure Blob service client operations used by the client factory."""

    def get_container_client(self, container: str) -> AzureBlobContainerClient: ...

    def close(self) -> None: ...


class AzureBlobContainerClient(Protocol):
    """Subset of Azure Blob container operations used by document storage."""

    def get_blob_client(self, blob: str) -> AzureBlobClient: ...


class AzureBlobDownloadStream(Protocol):
    """Subset of Azure Blob download stream operations used by document storage."""

    def readall(self) -> bytes: ...


class AzureBlobClient(Protocol):
    """Subset of Azure Blob client operations used by document storage."""

    def upload_blob(
        self,
        data: bytes,
        *,
        overwrite: bool,
        content_settings: object | None = None,
        timeout: float | None = None,
    ) -> object: ...

    def delete_blob(self, *, timeout: float | None = None) -> object: ...

    def download_blob(self, *, timeout: float | None = None) -> AzureBlobDownloadStream: ...


class AzureBlobDocumentStorageClient(DocumentContentStorage):
    """Store raw document content in Azure Blob Storage."""

    def __init__(
        self,
        *,
        container_name: str,
        blob_prefix: str,
        client_factory: AzureBlobClientFactory,
        operation_timeout_seconds: float,
        content_settings_factory: Callable[[str | None], object | None] | None = None,
    ) -> None:
        self._container_name = _normalize_container_name(container_name)
        self._blob_prefix = blob_prefix.strip("/")
        self._client_factory = client_factory
        self._operation_timeout_seconds = operation_timeout_seconds
        self._content_settings_factory = content_settings_factory or _content_settings

    async def save(self, command: StoreDocumentContentCommand) -> StorageLocator:
        """Persist content and return a stable Azure Blob locator."""

        blob_name = self._blob_name(command)
        blob_client = self._client_factory.container_client().get_blob_client(blob_name)
        content_settings = self._content_settings_factory(command.content_type)
        try:
            await asyncio.to_thread(
                blob_client.upload_blob,
                command.content,
                overwrite=False,
                content_settings=content_settings,
                timeout=self._operation_timeout_seconds,
            )
        except Exception as error:
            if _is_azure_error(error):
                raise DocumentContentStorageError(str(error)) from error
            raise

        return StorageLocator(_azure_blob_locator(self._container_name, blob_name))

    async def delete(self, locator: StorageLocator) -> None:
        """Delete previously stored Azure Blob content."""

        container_name, blob_name = _parse_azure_blob_locator(locator)
        if container_name != self._container_name:
            raise DocumentContentStorageError(
                "Storage locator points to a different Azure Blob container.",
            )

        blob_client = self._client_factory.container_client().get_blob_client(blob_name)
        try:
            await asyncio.to_thread(
                blob_client.delete_blob,
                timeout=self._operation_timeout_seconds,
            )
        except Exception as error:
            if _is_azure_resource_not_found(error):
                return
            if _is_azure_error(error):
                raise DocumentContentStorageError(str(error)) from error
            raise

    async def load(self, locator: StorageLocator) -> StoredDocumentContent:
        """Load stored content from an Azure Blob locator."""

        container_name, blob_name = _parse_azure_blob_locator(locator)
        if container_name != self._container_name:
            raise DocumentContentStorageError(
                "Storage locator points to a different Azure Blob container.",
            )
        self._validate_blob_name_for_load(blob_name)

        blob_client = self._client_factory.container_client().get_blob_client(blob_name)
        try:
            content = await asyncio.to_thread(
                lambda: blob_client.download_blob(
                    timeout=self._operation_timeout_seconds,
                ).readall(),
            )
        except Exception as error:
            if _is_azure_resource_not_found(error):
                raise DocumentContentStorageNotFoundError(str(error)) from error
            if _is_azure_error(error):
                raise DocumentContentStorageError(str(error)) from error
            raise

        return StoredDocumentContent(content=content)

    def _blob_name(self, command: StoreDocumentContentCommand) -> str:
        path_parts = [
            *self._blob_prefix_parts(),
            command.source.source,
            command.source.connector,
            str(command.document_id),
            _safe_filename(command.original_filename),
        ]
        return "/".join(_safe_blob_path_part(part) for part in path_parts if part)

    async def close(self) -> None:
        """Close SDK resources owned by the Azure Blob client factory."""

        await asyncio.to_thread(self._client_factory.close)

    def _blob_prefix_parts(self) -> tuple[str, ...]:
        return tuple(part for part in self._blob_prefix.split("/") if part)

    def _validate_blob_name_for_load(self, blob_name: str) -> None:
        prefix = "/".join(_safe_blob_path_part(part) for part in self._blob_prefix_parts())
        if prefix and not blob_name.startswith(f"{prefix}/"):
            raise DocumentContentStorageError(
                "Storage locator is outside configured Azure Blob prefix.",
            )


class AzureSdkBlobClientFactory(AzureBlobClientFactory):
    """Factory backed by the Azure Storage Blob SDK."""

    def __init__(
        self,
        *,
        account_url: str | None,
        connection_string: str | None,
        container_name: str,
        network_timeout_seconds: float,
    ) -> None:
        self._container_name = container_name
        self._credential: object | None
        (
            self._service_client,
            self._credential,
        ) = _create_azure_blob_service_client(
            account_url=account_url,
            connection_string=connection_string,
            network_timeout_seconds=network_timeout_seconds,
        )

    def container_client(self) -> AzureBlobContainerClient:
        return self._service_client.get_container_client(self._container_name)

    def close(self) -> None:
        self._service_client.close()
        if self._credential is not None:
            close = getattr(self._credential, "close", None)
            if callable(close):
                close()


def _create_azure_blob_service_client(
    *,
    account_url: str | None,
    connection_string: str | None,
    network_timeout_seconds: float,
) -> tuple[AzureBlobServiceClient, object | None]:
    from azure.core.pipeline.transport import RequestsTransport

    transport = RequestsTransport(
        connection_timeout=network_timeout_seconds,
        read_timeout=network_timeout_seconds,
    )
    if connection_string is not None:
        from azure.storage.blob import BlobServiceClient

        return (
            cast(
                AzureBlobServiceClient,
                BlobServiceClient.from_connection_string(
                    connection_string,
                    transport=transport,
                ),
            ),
            None,
        )

    if account_url is None:
        raise DocumentContentStorageError("Azure Blob account URL is required.")

    from azure.identity import DefaultAzureCredential
    from azure.storage.blob import BlobServiceClient

    credential = DefaultAzureCredential()
    return (
        cast(
            AzureBlobServiceClient,
            BlobServiceClient(
                account_url=account_url,
                credential=credential,
                transport=transport,
            ),
        ),
        credential,
    )


def _content_settings(content_type: str | None) -> object | None:
    if content_type is None:
        return None

    from azure.storage.blob import ContentSettings

    return ContentSettings(content_type=content_type)


def _is_azure_error(error: Exception) -> bool:
    from azure.core.exceptions import AzureError

    return isinstance(error, AzureError)


def _is_azure_resource_not_found(error: Exception) -> bool:
    from azure.core.exceptions import ResourceNotFoundError

    return isinstance(error, ResourceNotFoundError)


def _normalize_container_name(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise DocumentContentStorageError("Azure Blob container name is required.")
    return normalized


def _safe_blob_path_part(value: str) -> str:
    normalized = value.strip().strip("/")
    if not normalized:
        return "_"
    return quote(normalized.replace("\\", "/"), safe="-_.")


def _azure_blob_locator(container_name: str, blob_name: str) -> str:
    return f"{_AZURE_BLOB_LOCATOR_SCHEME}://{container_name}/{quote(blob_name, safe='/-_.')}"


def _parse_azure_blob_locator(locator: StorageLocator) -> tuple[str, str]:
    parsed = urlsplit(locator.value)
    if parsed.scheme != _AZURE_BLOB_LOCATOR_SCHEME or not parsed.netloc or not parsed.path:
        raise DocumentContentStorageError("Storage locator is not an Azure Blob locator.")

    return parsed.netloc, unquote(parsed.path.lstrip("/"))
