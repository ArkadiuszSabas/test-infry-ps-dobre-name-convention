import assert from "node:assert/strict";
import test from "node:test";

import type { InboxDocument } from "./types";
import {
  ALL_DOCUMENT_TYPES_VALUE,
  ALL_STATUSES_VALUE,
  getDocumentTypeFilters,
  getStatusFilters,
  getVisibleInboxDocuments,
} from "./list-view";

const documents: InboxDocument[] = [
  documentFixture({
    documentTypeId: "invoice-type",
    documentTypeName: "Invoice",
    id: "invoice-1",
    name: "Invoice 2026/01",
    originalFilename: "invoice-alpha.pdf",
    status: "received",
  }),
  documentFixture({
    connector: "email",
    connectorName: "Email",
    documentTypeId: "contract-type",
    documentTypeName: "Contract",
    id: "contract-1",
    name: "Master services agreement",
    originalFilename: "msa.pdf",
    status: "approved",
  }),
  documentFixture({
    documentTypeId: "invoice-type",
    documentTypeName: "Invoice",
    id: "invoice-2",
    name: "Invoice 2026/02",
    originalFilename: "invoice-beta.pdf",
    status: "review",
  }),
  documentFixture({
    documentTypeId: "orphan-type",
    documentTypeName: undefined,
    id: "orphan-1",
    name: "Legacy upload",
    originalFilename: "legacy.pdf",
    status: "received",
  }),
];

test("visible inbox documents apply type, status, and localized status search", () => {
  assert.deepEqual(
    getVisibleInboxDocuments(
      documents,
      "invoice-type",
      ALL_STATUSES_VALUE,
      "needs review",
      (document) =>
        document.status === "review" ? "Needs review" : document.status,
    ).map((document) => document.id),
    ["invoice-2"],
  );

  assert.deepEqual(
    getVisibleInboxDocuments(
      documents,
      ALL_DOCUMENT_TYPES_VALUE,
      "received",
      "legacy",
    ).map((document) => document.id),
    ["orphan-1"],
  );
});

test("document type filters count documents and fall back to type id", () => {
  assert.deepEqual(getDocumentTypeFilters(documents), [
    { count: 1, id: "contract-type", name: "Contract" },
    { count: 2, id: "invoice-type", name: "Invoice" },
    { count: 1, id: "orphan-type", name: "orphan-type" },
  ]);
});

test("status filters count statuses in deterministic order", () => {
  assert.deepEqual(getStatusFilters(documents), [
    { count: 1, status: "approved" },
    { count: 2, status: "received" },
    { count: 1, status: "review" },
  ]);
});

function documentFixture(
  overrides: Partial<InboxDocument> = {},
): InboxDocument {
  return {
    connector: "manual_upload",
    connectorCorrelationId: null,
    connectorName: "Manual upload",
    contentSizeBytes: 1024,
    createdAt: "2026-07-01T09:00:00Z",
    documentTypeExternalId: null,
    documentTypeId: "document-type",
    documentTypeName: "Document type",
    externalId: null,
    id: "document-id",
    metadataValues: {},
    name: "Document",
    originalFilename: "document.pdf",
    source: "manual_upload",
    status: "received",
    updatedAt: "2026-07-01T09:00:00Z",
    uploadedBy: null,
    ...overrides,
    archiveUrl: overrides.archiveUrl ?? null,
  };
}
