import { apiFetch, apiFetchBinary, buildApiUrl } from "@/lib/api/client";
import { unwrapEnvelope } from "@/lib/api/envelope";

import {
  OCR_PIPELINE_RUN_HISTORY_LIMIT,
  ocrPipelineRunClient,
} from "./ocr-pipeline-runs-api";
import {
  mapInboxDocumentEnvelope,
  mapInboxDocumentListEnvelope,
  mapDocumentTypeChangeEnvelope,
  mapManualUploadDictionaryEntry,
  mapManualUploadDictionaryEntryListEnvelope,
  mapManualUploadMetadataSchemaEnvelope,
  mapManualUploadOptionsEnvelope,
} from "./api-mappers";
import type {
  DocumentMetadataSchemaEnvelope,
  DocumentDeletionEnvelope,
  DocumentDeletionImpactEnvelope,
  InboxDocumentContext,
  InboxDocument,
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
  ManualUploadMetadataValue,
  ManualUploadOptionsEnvelope,
  ManualUploadOptionsEnvelopeDto,
} from "./types";

export const INBOX_DOCUMENT_LIST_LIMIT = 50;
export const INBOX_DOCUMENT_DETAIL_LOOKUP_LIMIT = 100;
export { OCR_PIPELINE_RUN_HISTORY_LIMIT };
export const MANUAL_UPLOAD_DICTIONARY_LOOKUP_LIMIT = 100;

export interface InboxRequestOptions {
  signal?: AbortSignal;
  csrfToken?: string | null;
}

export interface InboxDocumentListRequestOptions extends InboxRequestOptions {
  archived?: boolean;
  limit?: number;
  offset?: number;
}

export interface ManualUploadDictionaryLookupRequestOptions extends InboxRequestOptions {
  limit?: number;
  offset?: number;
  search?: string;
}

export const inboxClient = {
  async listDocuments(
    options: InboxDocumentListRequestOptions = {},
  ): Promise<InboxDocumentListEnvelope> {
    const params = new URLSearchParams({
      archived: String(options.archived ?? false),
      limit: String(options.limit ?? INBOX_DOCUMENT_LIST_LIMIT),
      offset: String(options.offset ?? 0),
    });

    return mapInboxDocumentListEnvelope(
      await apiFetch<InboxDocumentListEnvelopeDto>(
        `/documents?${params.toString()}`,
        {
          method: "GET",
          signal: options.signal,
        },
      ),
    );
  },

  async findDocumentContext(
    documentId: string,
    options: InboxDocumentListRequestOptions = {},
  ): Promise<InboxDocumentContext> {
    const documents: InboxDocument[] = [];
    let offset = 0;

    for (;;) {
      const page = await inboxClient.listDocuments({
        archived: options.archived,
        limit: INBOX_DOCUMENT_DETAIL_LOOKUP_LIMIT,
        offset,
        signal: options.signal,
      });
      const pageDocuments = page.data.documents;

      documents.push(...pageDocuments);

      const currentIndex = documents.findIndex(
        (document) => document.id === documentId,
      );
      const foundWithKnownNextDocument =
        currentIndex >= 0 && currentIndex < documents.length - 1;

      if (foundWithKnownNextDocument || !page.meta.hasMore) {
        return { documents };
      }

      if (page.meta.returnedCount <= 0) {
        return { documents };
      }

      offset = page.meta.offset + page.meta.returnedCount;
    }
  },

  async getDocument(
    documentId: string,
    options: InboxRequestOptions = {},
  ): Promise<InboxDocument> {
    return mapInboxDocumentEnvelope(
      await apiFetch<InboxDocumentEnvelopeDto>(
        `/documents/${encodeURIComponent(documentId)}`,
        {
          method: "GET",
          signal: options.signal,
        },
      ),
    );
  },

  async changeDocumentType(
    documentId: string,
    input: { confirmImpact: boolean; documentTypeId: string },
    options: InboxRequestOptions = {},
  ): Promise<DocumentTypeChangeEnvelope> {
    return mapDocumentTypeChangeEnvelope(
      await apiFetch<DocumentTypeChangeEnvelopeDto>(
        `/documents/${encodeURIComponent(documentId)}/document-type`,
        {
          csrfToken: options.csrfToken,
          json: {
            confirm_impact: input.confirmImpact,
            document_type_id: input.documentTypeId,
          },
          method: "PATCH",
          signal: options.signal,
        },
      ),
    );
  },

  async getDocumentDeletionImpact(
    documentId: string,
    options: InboxRequestOptions = {},
  ): Promise<DocumentDeletionImpactEnvelope> {
    return await apiFetch<DocumentDeletionImpactEnvelope>(
      `/documents/${encodeURIComponent(documentId)}/deletion`,
      {
        method: "GET",
        signal: options.signal,
      },
    );
  },

  async deleteDocument(
    documentId: string,
    options: InboxRequestOptions = {},
  ): Promise<DocumentDeletionEnvelope> {
    return await apiFetch<DocumentDeletionEnvelope>(
      `/documents/${encodeURIComponent(documentId)}`,
      {
        csrfToken: options.csrfToken,
        method: "DELETE",
        signal: options.signal,
      },
    );
  },

  async listManualUploadOptions(
    options: InboxRequestOptions = {},
  ): Promise<ManualUploadOptionsEnvelope> {
    return mapManualUploadOptionsEnvelope(
      await apiFetch<ManualUploadOptionsEnvelopeDto>(
        "/documents/manual-upload-options",
        {
          method: "GET",
          signal: options.signal,
        },
      ),
    );
  },

  async getManualUploadMetadataSchema(
    documentTypeId: string,
    options: InboxRequestOptions = {},
  ): Promise<ManualUploadMetadataSchemaEnvelope> {
    const params = new URLSearchParams({ document_type_id: documentTypeId });

    return mapManualUploadMetadataSchemaEnvelope(
      await apiFetch<ManualUploadMetadataSchemaEnvelopeDto>(
        `/documents/manual-upload-metadata-schema?${params.toString()}`,
        {
          method: "GET",
          signal: options.signal,
        },
      ),
    );
  },

  async getDocumentMetadataSchema(
    documentTypeId: string,
    options: InboxRequestOptions = {},
  ): Promise<DocumentMetadataSchemaEnvelope> {
    return mapManualUploadMetadataSchemaEnvelope(
      await apiFetch<ManualUploadMetadataSchemaEnvelopeDto>(
        `/document-types/${encodeURIComponent(documentTypeId)}/metadata-schema`,
        {
          method: "GET",
          signal: options.signal,
        },
      ),
    );
  },

  async listDictionaryLookupEntries(
    dictionaryId: string,
    options: ManualUploadDictionaryLookupRequestOptions = {},
  ): Promise<ManualUploadDictionaryEntryListEnvelope> {
    const entries: ManualUploadDictionaryEntryListEnvelope["data"]["entries"] =
      [];
    const initialOffset = options.offset ?? 0;
    const limit = options.limit ?? MANUAL_UPLOAD_DICTIONARY_LOOKUP_LIMIT;
    let offset = initialOffset;
    let lastMeta: ManualUploadDictionaryEntryListEnvelope["meta"] | null = null;

    for (;;) {
      const page = await listDictionaryLookupEntriesPage(dictionaryId, {
        ...options,
        limit,
        offset,
      });

      entries.push(...page.data.entries);
      lastMeta = page.meta;

      if (!page.meta.hasMore || page.meta.returnedCount <= 0) {
        break;
      }

      offset = page.meta.offset + page.meta.returnedCount;
    }

    return {
      data: { entries },
      meta: {
        hasMore: false,
        limit,
        offset: initialOffset,
        returnedCount: entries.length,
        totalCount: lastMeta?.totalCount ?? entries.length,
      },
    };
  },

  async resolveDictionaryLookupEntry(
    dictionaryId: string,
    entryExternalId: string,
    options: InboxRequestOptions = {},
  ): Promise<ManualUploadDictionaryEntry> {
    const params = new URLSearchParams({
      entry_external_id: entryExternalId,
    });

    return mapManualUploadDictionaryEntry(
      unwrapEnvelope(
        await apiFetch<ManualUploadDictionaryEntryEnvelopeDto>(
          `/dictionaries/${encodeURIComponent(dictionaryId)}/lookup/entries/resolve?${params.toString()}`,
          {
            method: "GET",
            signal: options.signal,
          },
        ),
      ),
    );
  },

  async uploadManualPdf(
    input: {
      documentTypeId: string;
      file: File;
      metadataValues: Record<string, ManualUploadMetadataValue>;
    },
    options: InboxRequestOptions = {},
  ): Promise<InboxDocument> {
    const formData = new FormData();
    formData.set("document_type_id", input.documentTypeId);
    formData.set("metadata_values", JSON.stringify(input.metadataValues));
    formData.set("file", input.file);

    return mapInboxDocumentEnvelope(
      await apiFetch<InboxDocumentEnvelopeDto>("/documents/manual-upload", {
        body: formData,
        csrfToken: options.csrfToken,
        method: "POST",
        signal: options.signal,
      }),
    );
  },

  buildDocumentPdfPreviewUrl(documentId: string): string {
    return buildApiUrl(`/documents/${encodeURIComponent(documentId)}/file`);
  },

  async loadDocumentPdfPreview(
    documentId: string,
    options: InboxRequestOptions = {},
  ): Promise<Blob> {
    return await apiFetchBinary(
      `/documents/${encodeURIComponent(documentId)}/file`,
      {
        expectedContentType: "application/pdf",
        method: "GET",
        signal: options.signal,
      },
    );
  },

  ...ocrPipelineRunClient,
};

async function listDictionaryLookupEntriesPage(
  dictionaryId: string,
  options: ManualUploadDictionaryLookupRequestOptions,
): Promise<ManualUploadDictionaryEntryListEnvelope> {
  const params = new URLSearchParams({
    limit: String(options.limit ?? MANUAL_UPLOAD_DICTIONARY_LOOKUP_LIMIT),
    offset: String(options.offset ?? 0),
  });
  if (options.search) {
    params.set("search", options.search);
  }

  return mapManualUploadDictionaryEntryListEnvelope(
    await apiFetch<ManualUploadDictionaryEntryListEnvelopeDto>(
      `/dictionaries/${encodeURIComponent(dictionaryId)}/lookup/entries?${params.toString()}`,
      {
        method: "GET",
        signal: options.signal,
      },
    ),
  );
}
