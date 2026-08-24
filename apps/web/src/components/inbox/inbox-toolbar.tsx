"use client";

import { useTranslations } from "next-intl";

import {
  DataListActions,
  DataListFilters,
  DataListToolbar,
} from "@/components/ui/data-list";
import {
  DataListChipFilter,
  DataListSearchFilter,
} from "@/components/ui/data-list-filters";
import { DocumentTypeDisplayFilter } from "@/components/system-catalogs/document-type-display-filter";
import type { DocumentTypeDisplayItem } from "@/lib/system-catalogs/document-type-display";
import type {
  DocumentStatus,
  ManualUploadDictionaryEntry,
  ManualUploadMetadataField,
  ManualUploadMetadataValue,
} from "@/lib/inbox/types";
import type { SystemCatalogDefinition } from "@/lib/system-catalogs/types";
import {
  ALL_DOCUMENT_TYPES_VALUE,
  ALL_STATUSES_VALUE,
  type InboxStatusFilter,
} from "@/lib/inbox/list-view";

import { InboxUploadControls } from "./inbox-upload-controls";

interface InboxToolbarProps {
  activeDocumentTypeId: string;
  canUpload: boolean;
  documentCount: number;
  documentTypeDefinition: SystemCatalogDefinition | null;
  documentTypeFilter: string;
  documentTypeFilterOptions: readonly DocumentTypeDisplayItem[];
  documentTypeOptions: readonly DocumentTypeDisplayItem[];
  dictionaryOptionsById: Record<string, readonly ManualUploadDictionaryEntry[]>;
  hasOptionsError: boolean;
  isOptionsPending: boolean;
  isUploadSheetOpen: boolean;
  isUploading: boolean;
  metadataFields: readonly ManualUploadMetadataField[];
  onDocumentTypeChange: (documentTypeId: string) => void;
  onDocumentTypeFilterChange: (value: string) => void;
  onOpenChange: (open: boolean) => void;
  onSearchChange: (value: string) => void;
  onStatusFilterChange: (value: string) => void;
  onUpload: (draft: {
    file: File;
    metadataValues: Record<string, ManualUploadMetadataValue>;
  }) => void;
  optionsError: string | null;
  search: string;
  statusFilter: InboxStatusFilter;
  statusFilters: readonly { count: number; status: DocumentStatus }[];
  uploadDisabled: boolean;
  uploadError: string | null;
}

export function InboxToolbar({
  activeDocumentTypeId,
  canUpload,
  documentCount,
  documentTypeDefinition,
  documentTypeFilter,
  documentTypeFilterOptions,
  documentTypeOptions,
  dictionaryOptionsById,
  hasOptionsError,
  isOptionsPending,
  isUploadSheetOpen,
  isUploading,
  metadataFields,
  onDocumentTypeChange,
  onDocumentTypeFilterChange,
  onOpenChange,
  onSearchChange,
  onStatusFilterChange,
  onUpload,
  optionsError,
  search,
  statusFilter,
  statusFilters,
  uploadDisabled,
  uploadError,
}: InboxToolbarProps) {
  const t = useTranslations("Inbox");
  const collection = useTranslations("CollectionView");

  return (
    <DataListToolbar>
      <DataListFilters>
        <DataListChipFilter
          ariaLabel={t("filters.status")}
          onValueChange={onStatusFilterChange}
          options={[
            {
              label: t("filters.allStatuses", { count: documentCount }),
              value: ALL_STATUSES_VALUE,
            },
            ...statusFilters.map((filter) => ({
              label: t("filters.statusValue", {
                count: filter.count,
                status: t(`status.${filter.status}`),
              }),
              value: filter.status,
            })),
          ]}
          value={statusFilter}
        />
        <DocumentTypeDisplayFilter
          ariaLabel={t("filters.documentTypes")}
          definition={documentTypeDefinition}
          displayModeAriaLabel={t("filters.displayMode")}
          displayModePlaceholder={t("filters.displayMode")}
          emptyMessage={collection("noResults")}
          onValueChange={onDocumentTypeFilterChange}
          options={[
            {
              id: ALL_DOCUMENT_TYPES_VALUE,
              label: t("filters.allDocumentTypesLabel"),
            },
            ...documentTypeFilterOptions,
          ]}
          placeholder={t("filters.documentTypes")}
          searchPlaceholder={collection("search")}
          value={documentTypeFilter}
        />
        <DataListSearchFilter
          ariaLabel={collection("search")}
          onValueChange={onSearchChange}
          placeholder={collection("search")}
          value={search}
        />
      </DataListFilters>

      {canUpload ? (
        <DataListActions>
          <InboxUploadControls
            activeDocumentTypeId={activeDocumentTypeId}
            documentTypeDefinition={documentTypeDefinition}
            documentTypeOptions={documentTypeOptions}
            dictionaryOptionsById={dictionaryOptionsById}
            hasOptionsError={hasOptionsError}
            isOptionsPending={isOptionsPending}
            isOpen={isUploadSheetOpen}
            isUploading={isUploading}
            metadataFields={metadataFields}
            onDocumentTypeChange={onDocumentTypeChange}
            onOpenChange={onOpenChange}
            onUpload={onUpload}
            optionsError={optionsError}
            uploadDisabled={uploadDisabled}
            uploadError={uploadError}
          />
        </DataListActions>
      ) : null}
    </DataListToolbar>
  );
}
