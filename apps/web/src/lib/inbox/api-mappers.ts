import { unwrapEnvelope } from "@/lib/api/envelope";

import type {
  InboxDocument,
  InboxDocumentDto,
  InboxDocumentEnvelopeDto,
  InboxDocumentListEnvelope,
  InboxDocumentListEnvelopeDto,
  DocumentTypeChangeEnvelope,
  DocumentTypeChangeEnvelopeDto,
  ManualUploadDictionaryEntry,
  ManualUploadDictionaryEntryEnvelopeDto,
  ManualUploadDictionaryEntryListEnvelope,
  ManualUploadDictionaryEntryListEnvelopeDto,
  ManualUploadMetadataSchemaEnvelope,
  ManualUploadMetadataSchemaEnvelopeDto,
  ManualUploadOptionsEnvelope,
  ManualUploadOptionsEnvelopeDto,
} from "./types";

export function mapInboxDocumentEnvelope(
  envelope: InboxDocumentEnvelopeDto,
): InboxDocument {
  return mapInboxDocument(unwrapEnvelope(envelope));
}

export function mapDocumentTypeChangeEnvelope(
  envelope: DocumentTypeChangeEnvelopeDto,
): DocumentTypeChangeEnvelope {
  return {
    data: {
      document: mapInboxDocument(envelope.data.document),
      impact: {
        addedFields: envelope.data.impact.added_fields,
        removedFields: envelope.data.impact.removed_fields,
        reprocessingRequested: envelope.data.impact.reprocessing_requested,
        requirednessChangedFields:
          envelope.data.impact.requiredness_changed_fields,
        requiresConfirmation: envelope.data.impact.requires_confirmation,
      },
    },
    meta: envelope.meta,
  };
}

export function mapInboxDocumentListEnvelope(
  envelope: InboxDocumentListEnvelopeDto,
): InboxDocumentListEnvelope {
  return {
    data: {
      documents: envelope.data.documents.map(mapInboxDocument),
    },
    meta: {
      hasMore: envelope.meta.has_more,
      limit: envelope.meta.limit,
      offset: envelope.meta.offset,
      returnedCount: envelope.meta.returned_count,
      source: envelope.meta.source,
    },
  };
}

export function mapManualUploadOptionsEnvelope(
  envelope: ManualUploadOptionsEnvelopeDto,
): ManualUploadOptionsEnvelope {
  return {
    data: {
      documentTypes: envelope.data.document_types.map((documentType) => ({
        externalId: documentType.external_id,
        id: documentType.id,
        name: documentType.name,
      })),
    },
    meta: {
      returnedCount: envelope.meta.returned_count,
    },
  };
}

export function mapManualUploadMetadataSchemaEnvelope(
  envelope: ManualUploadMetadataSchemaEnvelopeDto,
): ManualUploadMetadataSchemaEnvelope {
  return {
    data: {
      documentType: {
        externalId: envelope.data.document_type.external_id,
        id: envelope.data.document_type.id,
        name: envelope.data.document_type.name,
        status: envelope.data.document_type.status,
      },
      fields: envelope.data.fields.map((field) => ({
        allowedValues: field.allowed_values,
        category: field.category,
        categoryId: field.category_id,
        constraints: field.constraints,
        createdAt: field.created_at,
        dataType: field.data_type,
        dictionaryId: field.dictionary_id,
        externalId: field.external_id,
        id: field.id,
        key: field.key,
        label: field.label,
        required: field.required,
        schemaVersion: field.schema_version,
        status: field.status,
        updatedAt: field.updated_at,
        valueSource: field.value_source,
      })),
    },
    meta: {
      documentTypeId: envelope.meta.document_type_id,
      fieldCount: envelope.meta.field_count,
      requiredFieldCount: envelope.meta.required_field_count,
    },
  };
}

export function mapManualUploadDictionaryEntryListEnvelope(
  envelope: ManualUploadDictionaryEntryListEnvelopeDto,
): ManualUploadDictionaryEntryListEnvelope {
  return {
    data: {
      entries: envelope.data.entries.map(mapManualUploadDictionaryEntry),
    },
    meta: {
      hasMore: envelope.meta.has_more,
      limit: envelope.meta.limit,
      offset: envelope.meta.offset,
      returnedCount: envelope.meta.returned_count,
      totalCount: envelope.meta.total_count,
    },
  };
}

export function mapManualUploadDictionaryEntry(
  entry: ManualUploadDictionaryEntryEnvelopeDto["data"],
): ManualUploadDictionaryEntry {
  return {
    dictionaryId: entry.dictionary_id,
    externalId: entry.external_id,
    id: entry.id,
    label: entry.label,
    sortOrder: entry.sort_order ?? null,
  };
}

function mapInboxDocument(document: InboxDocumentDto): InboxDocument {
  return {
    archiveUrl: document.archive_url ?? null,
    connector: document.connector,
    connectorCorrelationId: document.connector_correlation_id,
    connectorName: document.connector_name,
    contentSizeBytes: document.content_size_bytes,
    createdAt: document.created_at,
    documentTypeExternalId: document.document_type_external_id ?? null,
    documentTypeId: document.document_type_id,
    documentTypeName: document.document_type_name,
    externalId: document.external_id ?? null,
    id: document.id,
    metadataValues: document.metadata_values ?? {},
    name: document.name,
    originalFilename: document.original_filename,
    source: document.source,
    status: document.status,
    uploadedBy: document.uploaded_by
      ? {
          displayName: document.uploaded_by.display_name,
          userId: document.uploaded_by.user_id,
        }
      : null,
    updatedAt: document.updated_at,
  };
}
