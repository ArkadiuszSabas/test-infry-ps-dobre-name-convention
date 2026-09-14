import type { QueryClient } from "@tanstack/react-query";
import { useCallback, type Dispatch, type SetStateAction } from "react";

import { updateAttributeRequirementMatrixCache } from "@/lib/admin-settings/attribute-requirements-cache";
import { adminCatalogQueryKeys } from "@/lib/admin-settings/query-options";
import type {
  AttributeDefinition,
  AttributeRequirementMatrixEnvelope,
  MissingRequiredAction,
} from "@/lib/admin-settings/types";
import type {
  AttributeRequirementDraftRow,
  AttributeRequirementState,
} from "@/lib/admin-settings/view-model";

export interface AttributeMatrixDraft {
  documentTypeId: string;
  rows: AttributeRequirementDraftRow[];
}

interface UseAttributeMatrixDraftActionsOptions {
  documentTypeId: string | null;
  queryClient: QueryClient;
  resetSaveError: () => void;
  rows: readonly AttributeRequirementDraftRow[];
  setDraft: Dispatch<SetStateAction<AttributeMatrixDraft | null>>;
}

export function useAttributeMatrixDraftActions({
  documentTypeId,
  queryClient,
  resetSaveError,
  rows,
  setDraft,
}: UseAttributeMatrixDraftActionsOptions) {
  const updateRows = useCallback(
    (
      update: (
        row: AttributeRequirementDraftRow,
      ) => AttributeRequirementDraftRow,
    ) => {
      resetSaveError();
      if (!documentTypeId) {
        return;
      }
      setDraft({
        documentTypeId,
        rows: rows.map(update),
      });
    },
    [documentTypeId, resetSaveError, rows, setDraft],
  );

  const updateRowState = useCallback(
    (attributeId: string, state: AttributeRequirementState) => {
      updateRows((row) =>
        row.attribute.id === attributeId ? { ...row, state } : row,
      );
    },
    [updateRows],
  );

  const updateMetadataInclusion = useCallback(
    (attributeId: string, checked: boolean) => {
      updateRows((row) =>
        row.attribute.id === attributeId
          ? { ...row, includeMetadataInContextResolver: checked }
          : row,
      );
    },
    [updateRows],
  );

  const updateMissingRequiredAction = useCallback(
    (attributeId: string, missingRequiredAction: MissingRequiredAction) => {
      updateRows((row) =>
        row.attribute.id === attributeId
          ? { ...row, missingRequiredAction }
          : row,
      );
    },
    [updateRows],
  );

  const applyAttributeUpdate = useCallback(
    (attribute: AttributeDefinition, isMetadata: boolean) => {
      const updateDraftAttribute = (row: AttributeRequirementDraftRow) =>
        row.attribute.id === attribute.id
          ? {
              ...row,
              attribute: {
                ...row.attribute,
                category: attribute.category,
                externalId: attribute.externalId,
                isMetadata,
                name: attribute.name,
                status: attribute.status,
              },
              includeMetadataInContextResolver: isMetadata
                ? row.includeMetadataInContextResolver
                : false,
            }
          : row;

      setDraft((current) =>
        current?.documentTypeId === documentTypeId
          ? { ...current, rows: current.rows.map(updateDraftAttribute) }
          : current,
      );

      if (documentTypeId) {
        queryClient.setQueryData<AttributeRequirementMatrixEnvelope>(
          adminCatalogQueryKeys.attributeRequirementsDetail(documentTypeId),
          (current) =>
            current
              ? updateAttributeRequirementMatrixCache(
                  current,
                  attribute,
                  isMetadata,
                )
              : current,
        );
      }
    },
    [documentTypeId, queryClient, setDraft],
  );

  return {
    applyAttributeUpdate,
    updateMetadataInclusion,
    updateMissingRequiredAction,
    updateRowState,
  };
}
