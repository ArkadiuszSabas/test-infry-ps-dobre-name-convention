"use client";

import {
  EyeIcon,
  ExternalLinkIcon,
  MoreHorizontalIcon,
  Trash2Icon,
} from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  DataListRow,
  DataListSkeletonRows,
  DataListTable,
} from "@/components/ui/data-list";
import { IconTooltipButton } from "@/components/ui/icon-tooltip-button";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  SortableTableHead,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
  TruncatedTableText,
} from "@/components/ui/table";
import { TableEmptyState } from "@/components/ui/table-empty-state";
import { Link } from "@/i18n/navigation";
import { archiveFolderUrl } from "@/lib/inbox/archive-url";
import type { InboxDocument, InboxDocumentsSortField } from "@/lib/inbox/types";
import { formatFileSize } from "@/lib/inbox/view-model";

import { DocumentDeletionDialog } from "./document-deletion-dialog";

export interface DocumentsTableProps {
  canDelete: boolean;
  canUpload: boolean;
  documents: readonly InboxDocument[];
  emptyDescription?: string;
  emptyTitle?: string;
  formatDate: (value: string) => string;
  formatNumber: (
    value: number,
    options?: { maximumFractionDigits?: number },
  ) => string;
  isLoading: boolean;
  detailBasePath?: "/archive" | "/documents";
  listSearch?: string;
  onDocumentDeleted: () => Promise<void> | void;
  onSortChange: (sortBy: InboxDocumentsSortField) => void;
  sortBy: InboxDocumentsSortField;
  sortOrder: "asc" | "desc";
}

export function DocumentsTable({
  canDelete,
  canUpload,
  documents,
  emptyDescription,
  emptyTitle,
  formatDate,
  formatNumber,
  isLoading,
  detailBasePath = "/documents",
  listSearch = "",
  onDocumentDeleted,
  onSortChange,
  sortBy,
  sortOrder,
}: DocumentsTableProps) {
  const t = useTranslations("Inbox");
  const archive = useTranslations("Archive");
  const collection = useTranslations("CollectionView");
  const [documentToDelete, setDocumentToDelete] =
    useState<InboxDocument | null>(null);

  function sortLabel(column: InboxDocumentsSortField, label: string) {
    const nextDirection =
      sortBy === column && sortOrder === "asc" ? "desc" : "asc";

    return collection(`sort.${nextDirection}`, { column: label });
  }

  return (
    <>
      <DataListTable>
        <TableHeader>
          <TableRow className="border-0 hover:bg-transparent">
            <SortableTableHead
              active={sortBy === "name"}
              className="w-[28%]"
              direction={sortOrder}
              onSort={() => onSortChange("name")}
              sortLabel={sortLabel("name", t("table.columns.name"))}
            >
              {t("table.columns.name")}
            </SortableTableHead>
            <SortableTableHead
              active={sortBy === "document_type"}
              className="w-[15%]"
              direction={sortOrder}
              onSort={() => onSortChange("document_type")}
              sortLabel={sortLabel("document_type", t("table.columns.type"))}
            >
              {t("table.columns.type")}
            </SortableTableHead>
            <SortableTableHead
              active={sortBy === "source"}
              className="w-[15%]"
              direction={sortOrder}
              onSort={() => onSortChange("source")}
              sortLabel={sortLabel("source", t("table.columns.input"))}
            >
              {t("table.columns.input")}
            </SortableTableHead>
            <SortableTableHead
              active={sortBy === "status"}
              className="w-52"
              direction={sortOrder}
              onSort={() => onSortChange("status")}
              sortLabel={sortLabel("status", t("table.columns.status"))}
            >
              {t("table.columns.status")}
            </SortableTableHead>
            <SortableTableHead
              active={sortBy === "size"}
              className="w-20"
              direction={sortOrder}
              onSort={() => onSortChange("size")}
              sortLabel={sortLabel("size", t("table.columns.size"))}
            >
              {t("table.columns.size")}
            </SortableTableHead>
            <SortableTableHead
              active={sortBy === "created"}
              className="w-32"
              direction={sortOrder}
              onSort={() => onSortChange("created")}
              sortLabel={sortLabel("created", t("table.columns.created"))}
            >
              {t("table.columns.created")}
            </SortableTableHead>
            <TableHead className="w-12">
              <span className="sr-only">{t("table.columns.actions")}</span>
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {isLoading ? <LoadingRows /> : null}
          {!isLoading && documents.length === 0 ? (
            <TableEmptyState
              columns={7}
              description={
                emptyDescription ??
                (canUpload
                  ? t("empty.description")
                  : t("empty.readOnlyDescription"))
              }
              title={emptyTitle ?? t("empty.title")}
            />
          ) : null}
          {documents.map((document) => (
            <DataListRow key={document.id}>
              <TableCell className="w-[28%]">
                <Link
                  aria-label={t("table.preview", { name: document.name })}
                  className="flex min-w-0 flex-col gap-1 rounded-sm underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  href={detailHref(detailBasePath, document.id, listSearch)}
                >
                  <TruncatedTableText
                    className="font-medium"
                    value={document.name}
                  />
                  <TruncatedTableText
                    className="text-xs text-muted-foreground"
                    value={document.originalFilename}
                  />
                </Link>
              </TableCell>
              <TableCell className="w-[15%]">
                <TruncatedTableText
                  value={document.documentTypeName ?? document.documentTypeId}
                />
              </TableCell>
              <TableCell className="w-[15%]">
                <TruncatedTableText
                  value={document.connectorName ?? document.connector}
                />
              </TableCell>
              <TableCell className="w-52">
                <Badge variant="secondary">
                  {t(`status.${document.status}`)}
                </Badge>
              </TableCell>
              <TableCell className="w-20">
                {formatFileSize(
                  document.contentSizeBytes,
                  formatNumber,
                  t("table.unknownSize"),
                )}
              </TableCell>
              <TableCell className="w-32">
                {formatDate(document.createdAt)}
              </TableCell>
              <TableCell className="w-12 text-right">
                {canDelete || detailBasePath === "/archive" ? (
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <IconTooltipButton
                        tooltip={t("table.actionsFor", {
                          name: document.name,
                        })}
                        variant="secondary"
                      >
                        <MoreHorizontalIcon />
                      </IconTooltipButton>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem asChild>
                        <Link
                          href={detailHref(
                            detailBasePath,
                            document.id,
                            listSearch,
                          )}
                        >
                          <EyeIcon />
                          {t("table.previewMenu")}
                        </Link>
                      </DropdownMenuItem>
                      {detailBasePath === "/archive" ? (
                        <ArchiveLinkMenuItem
                          archiveUrl={document.archiveUrl}
                          label={archive("sharePoint.openFolder")}
                          unavailableLabel={archive("sharePoint.unavailable")}
                        />
                      ) : null}
                      {canDelete ? (
                        <DropdownMenuItem
                          className="text-destructive focus:text-destructive"
                          onSelect={() => setDocumentToDelete(document)}
                        >
                          <Trash2Icon />
                          {t("table.deleteMenu")}
                        </DropdownMenuItem>
                      ) : null}
                    </DropdownMenuContent>
                  </DropdownMenu>
                ) : (
                  <IconTooltipButton
                    asChild
                    tooltip={t("table.previewAction", {
                      name: document.name,
                    })}
                    variant="secondary"
                  >
                    <Link
                      aria-label={t("table.previewAction", {
                        name: document.name,
                      })}
                      href={detailHref(detailBasePath, document.id, listSearch)}
                    >
                      <EyeIcon />
                    </Link>
                  </IconTooltipButton>
                )}
              </TableCell>
            </DataListRow>
          ))}
        </TableBody>
      </DataListTable>
      <DocumentDeletionDialog
        document={documentToDelete}
        onDeleted={onDocumentDeleted}
        onOpenChange={(open) => {
          if (!open) {
            setDocumentToDelete(null);
          }
        }}
        open={documentToDelete !== null}
      />
    </>
  );
}

function detailHref(
  detailBasePath: "/archive" | "/documents",
  documentId: string,
  listSearch: string,
): string {
  return `${detailBasePath}/${documentId}${listSearch ? `?${listSearch}` : ""}`;
}

function ArchiveLinkMenuItem({
  archiveUrl,
  label,
  unavailableLabel,
}: {
  archiveUrl: string | null;
  label: string;
  unavailableLabel: string;
}) {
  if (archiveUrl) {
    return (
      <DropdownMenuItem asChild>
        <a href={archiveFolderUrl(archiveUrl)} rel="noreferrer" target="_blank">
          <ExternalLinkIcon />
          {label}
        </a>
      </DropdownMenuItem>
    );
  }

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span tabIndex={0}>
          <DropdownMenuItem disabled>
            <ExternalLinkIcon />
            {label}
          </DropdownMenuItem>
        </span>
      </TooltipTrigger>
      <TooltipContent>{unavailableLabel}</TooltipContent>
    </Tooltip>
  );
}

function LoadingRows() {
  return <DataListSkeletonRows columns={7} />;
}
