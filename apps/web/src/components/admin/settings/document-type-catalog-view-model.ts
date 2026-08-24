import type {
  DocumentTypeDefinition,
  UpdateDocumentTypeInput,
  UpsertDocumentTypeInput,
} from "@/lib/admin-settings/types";
import { applyCollectionView, type SortValue } from "@/lib/collection-view";

export type DocumentTypeFormState =
  | { kind: "create" }
  | { item: DocumentTypeDefinition; kind: "edit" };

export type DocumentTypeSaveVariables =
  | {
      input: UpsertDocumentTypeInput;
      kind: "create";
    }
  | {
      documentTypeId: string;
      input: UpdateDocumentTypeInput;
      kind: "edit";
    };

export function getVisibleDocumentTypes({
  documentTypes,
  search,
}: {
  documentTypes: readonly DocumentTypeDefinition[];
  search: string;
}): DocumentTypeDefinition[] {
  return applyCollectionView(documentTypes, {
    search,
    searchAccessors: [
      (documentType): SortValue => documentType.displayLabel,
      (documentType): SortValue => documentType.name,
      (documentType): SortValue => documentType.externalId,
      (documentType): SortValue => documentType.description,
      (documentType): SortValue =>
        documentType.parameters
          .map((parameter) =>
            `${parameter.label} ${parameter.value ?? ""}`.trim(),
          )
          .join(" "),
    ],
    sort: {
      accessor: (documentType) =>
        documentType.displayLabel ?? documentType.name,
    },
  });
}
