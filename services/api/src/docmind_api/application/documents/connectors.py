"""Input connector descriptors for document ingestion."""

from dataclasses import dataclass

from docmind_api.domain.documents.models import (
    MANUAL_UPLOAD_CONNECTOR,
    MANUAL_UPLOAD_CONNECTOR_INSTANCE_ID,
    MANUAL_UPLOAD_SOURCE,
    DocumentSource,
)

MANUAL_UPLOAD_CONNECTOR_DISPLAY_NAME = "Manual upload"


@dataclass(frozen=True, slots=True)
class DocumentInputConnector:
    """Stable descriptor for an input connector that can produce documents."""

    source: str
    connector: str
    connector_instance_id: str
    display_name: str

    def document_source(self, *, correlation_id: str | None = None) -> DocumentSource:
        """Return the registry source metadata for documents from this connector."""

        return DocumentSource(
            source=self.source,
            connector=self.connector,
            connector_instance_id=self.connector_instance_id,
            correlation_id=correlation_id,
        )

    def matches(self, source: str, connector: str) -> bool:
        """Return whether persisted source metadata belongs to this connector."""

        return source == self.source and connector == self.connector


@dataclass(frozen=True, slots=True)
class DocumentInputConnectorCatalog:
    """In-memory catalog for built-in input connector descriptors."""

    connectors: tuple[DocumentInputConnector, ...]

    def display_name_for(self, source: str, connector: str) -> str:
        """Return a connector display name, falling back to the stored connector id."""

        for input_connector in self.connectors:
            if input_connector.matches(source, connector):
                return input_connector.display_name

        return connector


MANUAL_UPLOAD_INPUT_CONNECTOR = DocumentInputConnector(
    source=MANUAL_UPLOAD_SOURCE,
    connector=MANUAL_UPLOAD_CONNECTOR,
    connector_instance_id=MANUAL_UPLOAD_CONNECTOR_INSTANCE_ID,
    display_name=MANUAL_UPLOAD_CONNECTOR_DISPLAY_NAME,
)
