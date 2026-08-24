"use client";

import {
  EyeIcon,
  ExternalLinkIcon,
  MoreHorizontalIcon,
  Trash2Icon,
} from "lucide-react";
import { useTranslations } from "next-intl";
import { useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
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
import {
  applyCollectionView,
  nextSortState,
  type SortState,
  type SortValue,
} from "@/lib/collection-view";
import { archiveFolderUrl } from "@/lib/inbox/archive-url";
import type { InboxDocument } from "@/lib/inbox/types";
import { formatFileSize } from "@/lib/inbox/view-model";

import { DocumentDeletionDialog } from "./document-deletion-dialog";

type DocumentsSortColumn =
  | "created"
  | "input"
  | "name"
  | "size"
  | "status"
  | "type";

const documentSortAccessors: Record<
  DocumentsSortColumn,
  (document: InboxDocument) => SortValue
> = {
  created: (document) => document.createdAt,
  input: (document) => document.connectorName ?? document.connector,
  name: (document) => document.name,
  size: (document) => document.contentSizeBytes,
  status: (document) => document.status,
  type: (document) => document.documentTypeName ?? document.documentTypeId,
};

const defaultDocumentsSort: SortState<DocumentsSortColumn> = {
  column: "created",
  direction: "desc",
};

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
  hasMore: boolean;
  isFetchingMore: boolean;
  isLoading: boolean;
  detailBasePath?: "/archive" | "/documents";
  onLoadMore: () => void;
  onDocumentDeleted: () => Promise<void> | void;
}

export function DocumentsTable({
  canDelete,
  canUpload,
  documents,
  emptyDescription,
  emptyTitle,
  formatDate,
  formatNumber,
  hasMore,
  isFetchingMore,
  isLoading,
  detailBasePath = "/documents",
  onLoadMore,
  onDocumentDeleted,
}: DocumentsTableProps) {
  const t = useTranslations("Inbox");
  const archive = useTranslations("Archive");
  const collection = useTranslations("CollectionView");
  const [sort, setSort] =
    useState<SortState<DocumentsSortColumn>>(defaultDocumentsSort);
  const [documentToDelete, setDocumentToDelete] =
    useState<InboxDocument | null>(null);
  const sortedDocuments = useMemo(
    () =>
      applyCollectionView(documents, {
        sort: {
          accessor: documentSortAccessors[sort.column],
          direction: sort.direction,
        },
      }),
    [documents, sort],
  );

  function sortLabel(column: DocumentsSortColumn, label: string) {
    const nextDirection =
      sort.column === column && sort.direction === "asc" ? "desc" : "asc";

    return collection(`sort.${nextDirection}`, { column: label });
  }

  return (
    <>
      <DataListTable>
        <TableHeader>
          <TableRow className="border-0 hover:bg-transparent">
            <SortableTableHead
              active={sort.column === "name"}
              className="w-[28%]"
              direction={sort.direction}
              onSort={() =>
                setSort((current) => nextSortState(current, "name"))
              }
              sortLabel={sortLabel("name", t("table.columns.name"))}
            >
              {t("table.columns.name")}
            </SortableTableHead>
            <SortableTableHead
              active={sort.column === "type"}
              className="w-[15%]"
              direction={sort.direction}
              onSort={() =>
                setSort((current) => nextSortState(current, "type"))
              }
              sortLabel={sortLabel("type", t("table.columns.type"))}
            >
              {t("table.columns.type")}
            </SortableTableHead>
            <SortableTableHead
              active={sort.column === "input"}
              className="w-[15%]"
              direction={sort.direction}
              onSort={() =>
                setSort((current) => nextSortState(current, "input"))
              }
              sortLabel={sortLabel("input", t("table.columns.input"))}
            >
              {t("table.columns.input")}
            </SortableTableHead>
            <SortableTableHead
              active={sort.column === "status"}
              className="w-52"
              direction={sort.direction}
              onSort={() =>
                setSort((current) => nextSortState(current, "status"))
              }
              sortLabel={sortLabel("status", t("table.columns.status"))}
            >
              {t("table.columns.status")}
            </SortableTableHead>
            <SortableTableHead
              active={sort.column === "size"}
              className="w-20"
              direction={sort.direction}
              onSort={() =>
                setSort((current) => nextSortState(current, "size"))
              }
              sortLabel={sortLabel("size", t("table.columns.size"))}
            >
              {t("table.columns.size")}
            </SortableTableHead>
            <SortableTableHead
              active={sort.column === "created"}
              className="w-32"
              direction={sort.direction}
              onSort={() =>
                setSort((current) => nextSortState(current, "created"))
              }
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
          {sortedDocuments.map((document) => (
            <DataListRow key={document.id}>
              <TableCell className="w-[28%]">
                <Link
                  aria-label={t("table.preview", { name: document.name })}
                  className="flex min-w-0 flex-col gap-1 rounded-sm underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  href={`${detailBasePath}/${document.id}`}
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
                        <Link href={`${detailBasePath}/${document.id}`}>
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
                      href={`${detailBasePath}/${document.id}`}
                    >
                      <EyeIcon />
                    </Link>
                  </IconTooltipButton>
                )}
              </TableCell>
            </DataListRow>
          ))}
          {!isLoading && hasMore ? (
            <TableRow className="border-0 hover:bg-transparent">
              <TableCell className="text-center" colSpan={7}>
                <Button
                  disabled={isFetchingMore}
                  onClick={onLoadMore}
                  type="button"
                  variant="outline"
                >
                  {isFetchingMore
                    ? t("table.loadingMore")
                    : t("table.loadMore")}
                </Button>
              </TableCell>
            </TableRow>
          ) : null}
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
