"""Storage reference resolvers for OCR provider calls."""

from urllib.parse import quote, unquote, urlsplit


class AzureBlobDocumentReferenceResolver:
    """Resolve safe Azure Blob storage references to provider-readable URLs."""

    def __init__(
        self,
        *,
        account_url: str | None,
    ) -> None:
        self._account_url = (account_url or "").rstrip("/")

    def resolve_provider_url(self, storage_reference: str) -> str:
        """Return an HTTPS blob URL for Azure Document Intelligence."""

        parsed = urlsplit(storage_reference)
        if parsed.scheme == "https":
            return storage_reference

        if parsed.scheme != "azblob" or not parsed.netloc or not parsed.path:
            raise ValueError("Unsupported OCR document storage reference.")
        if not self._account_url:
            raise ValueError("Azure Blob account URL is required for OCR document references.")

        container_name = parsed.netloc
        blob_path = unquote(parsed.path.lstrip("/"))
        encoded_blob_path = quote(blob_path, safe="/-_.")
        return f"{self._account_url}/{container_name}/{encoded_blob_path}"
