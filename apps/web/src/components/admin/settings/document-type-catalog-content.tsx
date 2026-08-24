"use client";

import { FileTextIcon } from "lucide-react";
import { useFormatter, useTranslations } from "next-intl";

import {
  CatalogNotice,
  CatalogStatusBadge,
  getCatalogErrorMessage,
} from "@/components/admin/catalog/catalog-shared";
import { Badge } from "@/components/ui/badge";
import {
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { DataListContent, DataListGrid } from "@/components/ui/data-list";
import { EmptyState } from "@/components/ui/empty-state";
import { IconFrame } from "@/components/ui/icon-frame";
import { PanelCard } from "@/components/ui/panel-card";
import { Skeleton } from "@/components/ui/skeleton";
import type { DocumentTypeDefinition } from "@/lib/admin-settings/types";

import { DocumentTypeCardActions } from "./document-type-card-actions";

interface DocumentTypeCatalogContentProps {
  documentTypes: readonly DocumentTypeDefinition[];
  hasActiveFilters: boolean;
  isError: boolean;
  isPending: boolean;
  loadError: unknown;
  onDeactivate: (documentType: DocumentTypeDefinition) => void;
  onDelete: (documentType: DocumentTypeDefinition) => void;
  onEdit: (documentType: DocumentTypeDefinition) => void;
  visibleDocumentTypes: readonly DocumentTypeDefinition[];
}

export function DocumentTypeCatalogContent({
  documentTypes,
  hasActiveFilters,
  isError,
  isPending,
  loadError,
  onDeactivate,
  onDelete,
  onEdit,
  visibleDocumentTypes,
}: DocumentTypeCatalogContentProps) {
  const t = useTranslations("AdminSettings.documentTypes");
  const common = useTranslations("AdminSettings.common");
  const collection = useTranslations("CollectionView");
  const format = useFormatter();

  return (
    <DataListContent>
      {isError ? (
        <CatalogNotice
          description={t("errorDescription")}
          title={getCatalogErrorMessage(loadError, t("errorTitle"))}
          tone="danger"
        />
      ) : null}

      {isPending ? (
        <DataListGrid>
          {Array.from({ length: 3 }, (_, index) => (
            <PanelCard key={index} size="sm">
              <CardContent className="flex flex-col gap-3 p-4">
                <Skeleton className="h-5 w-40" />
                <Skeleton className="h-4 w-24" />
                <Skeleton className="h-16 w-full" />
              </CardContent>
            </PanelCard>
          ))}
        </DataListGrid>
      ) : null}

      {!isPending && !isError && documentTypes.length === 0 ? (
        <EmptyState
          description={t("emptyDescription")}
          title={t("emptyTitle")}
        />
      ) : null}

      {!isPending &&
      !isError &&
      hasActiveFilters &&
      documentTypes.length > 0 &&
      visibleDocumentTypes.length === 0 ? (
        <EmptyState
          description={collection("noResultsDescription")}
          title={collection("noResults")}
        />
      ) : null}

      {visibleDocumentTypes.length > 0 ? (
        <DataListGrid>
          {visibleDocumentTypes.map((documentType) => (
            <PanelCard
              className="transition-colors hover:bg-accent/60"
              key={documentType.id}
              size="sm"
            >
              <CardHeader className="flex flex-row items-start justify-between gap-3">
                <div className="flex min-w-0 items-start gap-3">
                  <IconFrame icon={FileTextIcon} size="sm" />
                  <div className="min-w-0">
                    <CardTitle className="truncate">
                      {documentType.displayLabel}
                    </CardTitle>
                    <p className="mt-1 truncate text-xs text-muted-foreground">
                      {getDocumentTypeOverviewSummary(
                        documentType,
                        common("notSet"),
                      )}
                    </p>
                  </div>
                </div>
                <CatalogStatusBadge
                  label={common(`status.${documentType.status}`)}
                  status={documentType.status}
                />
              </CardHeader>

              <CardContent>
                <p className="min-h-10 text-muted-foreground">
                  {documentType.description || common("notSet")}
                </p>
                {documentType.parameters.length > 0 ? (
                  <div className="mt-4 flex flex-wrap gap-2">
                    {documentType.parameters.map((parameter) => (
                      <Badge
                        key={`${documentType.id}-${parameter.code}`}
                        variant="outline"
                      >
                        {parameter.label}: {parameter.value ?? common("notSet")}
                      </Badge>
                    ))}
                  </div>
                ) : null}
              </CardContent>

              <CardFooter className="justify-between gap-3 bg-transparent">
                <span className="text-xs text-muted-foreground">
                  {t("columns.updatedAt")}:{" "}
                  {format.dateTime(new Date(documentType.updatedAt), {
                    day: "2-digit",
                    month: "short",
                    year: "numeric",
                  })}
                </span>
                <DocumentTypeCardActions
                  documentType={documentType}
                  onDeactivate={onDeactivate}
                  onDelete={onDelete}
                  onEdit={onEdit}
                />
              </CardFooter>
            </PanelCard>
          ))}
        </DataListGrid>
      ) : null}
    </DataListContent>
  );
}

function getDocumentTypeOverviewSummary(
  documentType: DocumentTypeDefinition,
  fallback: string,
): string {
  return documentType.parameters[0]?.value?.trim() || fallback;
}
