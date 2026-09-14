import type {
  DocumentTypeDefinition,
  UpdateDocumentTypeInput,
  UpsertDocumentTypeInput,
} from "@/lib/admin-settings/types";

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
