"use client";

import { useQuery } from "@tanstack/react-query";

import { manualUploadOptionsQueryOptions } from "@/lib/inbox/query-options";
import type { ManualUploadDocumentType } from "@/lib/inbox/types";
import { getUploadDocumentTypeOptions } from "@/lib/inbox/view-model";
import { systemCatalogOptionsQueryOptions } from "@/lib/system-catalogs/query-options";
import type { SystemCatalogOption } from "@/lib/system-catalogs/types";

const EMPTY_DOCUMENT_TYPE_OPTIONS: SystemCatalogOption[] = [];
const EMPTY_MANUAL_UPLOAD_DOCUMENT_TYPES: ManualUploadDocumentType[] = [];

interface InboxDocumentTypeConfigurationInput {
  canReadSystemCatalogOptions: boolean;
  canUpload: boolean;
}

export function useInboxDocumentTypeConfiguration({
  canReadSystemCatalogOptions,
  canUpload,
}: InboxDocumentTypeConfigurationInput) {
  const manualUploadOptionsQuery = useQuery(
    manualUploadOptionsQueryOptions(canUpload),
  );
  const documentTypeOptionsQuery = useQuery(
    systemCatalogOptionsQueryOptions(
      "document_type",
      canReadSystemCatalogOptions,
    ),
  );
  const systemCatalogOptionData = documentTypeOptionsQuery.data?.data;
  const systemCatalogOptions =
    systemCatalogOptionData?.options ?? EMPTY_DOCUMENT_TYPE_OPTIONS;
  const manualUploadDocumentTypes =
    manualUploadOptionsQuery.data?.data.documentTypes ??
    EMPTY_MANUAL_UPLOAD_DOCUMENT_TYPES;
  const uploadDocumentTypeOptions = getUploadDocumentTypeOptions({
    manualUploadDocumentTypes,
    systemCatalogOptions,
  });

  return {
    documentTypeDefinition: systemCatalogOptionData?.definition ?? null,
    documentTypeOptions:
      systemCatalogOptions.length > 0
        ? systemCatalogOptions
        : uploadDocumentTypeOptions,
    uploadDocumentTypeOptions,
    uploadDocumentTypesError: manualUploadOptionsQuery.isError,
    uploadDocumentTypesErrorValue: manualUploadOptionsQuery.error,
    uploadDocumentTypesPending: manualUploadOptionsQuery.isPending,
  };
}
