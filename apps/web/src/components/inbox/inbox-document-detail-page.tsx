"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ChevronLeftIcon,
  ChevronRightIcon,
  FileCheck2Icon,
  FileTextIcon,
  ExternalLinkIcon,
  Trash2Icon,
} from "lucide-react";
import { useFormatter, useTranslations } from "next-intl";
import { useEffect, useState, type ReactNode } from "react";

import { DocumentDeletionDialog } from "@/components/inbox/document-deletion-dialog";
import {
  DocumentWorkspacePanel,
  type DocumentReviewState,
} from "@/components/inbox/inbox-document-workspace-panel";
import {
  getDocumentReviewPresentationKind,
  getDocumentReviewRefetchInterval,
} from "@/components/inbox/document-review-sync";
import { InboxNotice } from "@/components/inbox/inbox-notice";
import { InboxPdfViewer } from "@/components/inbox/inbox-pdf-viewer";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { PageBackLink } from "@/components/ui/page-back-link";
import { PageHeader } from "@/components/ui/page-header";
import { PageShell } from "@/components/ui/page-shell";
import { PanelCard } from "@/components/ui/panel-card";
import { Separator } from "@/components/ui/separator";
import { Spinner } from "@/components/ui/spinner";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { useCurrentActor } from "@/hooks/auth/use-current-actor";
import { Link, useRouter } from "@/i18n/navigation";
import { inboxClient } from "@/lib/inbox/api";
import { archiveFolderUrl } from "@/lib/inbox/archive-url";
import {
  getOcrPipelineRunHistoryRefetchInterval,
  isTerminalOcrPipelineRunStatus,
} from "@/lib/inbox/ocr-run-view-model";
import {
  documentDetailQueryOptions,
  documentMetadataSchemaQueryOptions,
  documentOcrPipelineRunsQueryOptions,
  inboxQueryKeys,
} from "@/lib/inbox/query-options";
import type { InboxDocument, OcrPipelineRunStatus } from "@/lib/inbox/types";
import {
  documentReviewQueryOptions,
  reviewQueryKeys,
} from "@/lib/review/query-options";
import type { DocumentReview } from "@/lib/review/types";
import {
  buildReviewWorkspaceViewModel,
  formatFallbackStatusLabel,
} from "@/lib/review/view-model";

export interface InboxDocumentDetailPageProps {
  approvalCompleted?: boolean;
  documentId: string;
  mode?: "archive" | "inbox";
}

const REVIEW_STATUS_LABEL_KEYS = [
  "approved",
  "in_review",
  "needs_changes",
  "received",
  "rejected",
] as const;

export function InboxDocumentDetailPage({
  approvalCompleted = false,
  documentId,
  mode = "inbox",
}: InboxDocumentDetailPageProps) {
  const t = useTranslations("Inbox");
  const archive = useTranslations("Archive");
  const review = useTranslations("ReviewWorkspace");
  const format = useFormatter();
  const queryClient = useQueryClient();
  const router = useRouter();
  const { actor } = useCurrentActor();
  const [isDeletionDialogOpen, setIsDeletionDialogOpen] = useState(false);
  const isArchive = mode === "archive";
  const collectionPath = isArchive ? "/archive" : "/documents";
  const documentsQuery = useQuery({
    queryKey: inboxQueryKeys.documentContext(documentId, isArchive),
    queryFn: ({ signal }) =>
      inboxClient.findDocumentContext(documentId, {
        archived: isArchive,
        signal,
      }),
    retry: false,
  });

  const documents = documentsQuery.data?.documents ?? [];
  const document = documents.find((candidate) => candidate.id === documentId);
  const detailQuery = useQuery({
    ...documentDetailQueryOptions(documentId, Boolean(document)),
    refetchOnMount: isArchive ? "always" : undefined,
  });
  const detailError = detailQuery.isError ? detailQuery.error : null;
  const activeDocument =
    detailQuery.data && document
      ? {
          ...detailQuery.data,
          documentTypeExternalId: document.documentTypeExternalId,
          documentTypeId: document.documentTypeId,
          documentTypeName: document.documentTypeName,
          status: document.status,
          updatedAt: document.updatedAt,
        }
      : (detailQuery.data ?? document);
  const canReadDocuments =
    actor?.permissions.includes("documents.read") ?? false;
  const canReview = actor?.permissions.includes("documents.review") ?? false;
  const canDelete = actor?.permissions.includes("documents.delete") ?? false;
  const metadataSchemaQuery = useQuery(
    documentMetadataSchemaQueryOptions(
      activeDocument?.documentTypeId ?? "",
      Boolean(activeDocument),
    ),
  );
  const pipelineRunsQuery = useQuery({
    ...documentOcrPipelineRunsQueryOptions(
      documentId,
      Boolean(document) && canReadDocuments,
    ),
    refetchInterval: (query) =>
      getOcrPipelineRunHistoryRefetchInterval(
        query.state.data?.data.runs[0]?.status ?? null,
      ),
  });
  const pipelineRuns = pipelineRunsQuery.data?.data.runs ?? [];
  const latestPipelineRun = pipelineRuns[0] ?? null;
  const reviewQuery = useQuery({
    ...documentReviewQueryOptions(documentId, Boolean(document) && canReview),
    refetchInterval: (query) =>
      getDocumentReviewRefetchInterval(
        latestPipelineRun?.status ?? null,
        query.state.data?.dataSource,
      ),
  });
  const terminalRunRefreshKey =
    latestPipelineRun &&
    isTerminalOcrPipelineRunStatus(latestPipelineRun.status)
      ? latestPipelineRun.id
      : null;

  useEffect(() => {
    if (!terminalRunRefreshKey) {
      return;
    }

    void queryClient.invalidateQueries({
      queryKey: reviewQueryKeys.document(documentId),
    });
  }, [documentId, queryClient, terminalRunRefreshKey]);
  const currentIndex = documents.findIndex(
    (candidate) => candidate.id === documentId,
  );
  const previousDocument =
    currentIndex > 0 ? documents[currentIndex - 1] : null;
  const nextDocument =
    currentIndex >= 0 && currentIndex < documents.length - 1
      ? documents[currentIndex + 1]
      : null;

  if (documentsQuery.isPending) {
    return (
      <DocumentStateShell mode={mode} title={t("detail.loading")}>
        <div className="flex min-h-[24rem] items-center justify-center gap-2 text-muted-foreground">
          <Spinner className="size-5" />
          <span className="text-sm">{t("detail.loading")}</span>
        </div>
      </DocumentStateShell>
    );
  }

  if (documentsQuery.isError) {
    return (
      <DocumentStateShell mode={mode} title={t("errors.loadTitle")}>
        <InboxNotice
          description={t("errors.loadDescription")}
          title={t("errors.loadTitle")}
          tone="danger"
        />
      </DocumentStateShell>
    );
  }

  if (!document || !activeDocument) {
    return (
      <DocumentStateShell mode={mode} title={t("detail.notFoundTitle")}>
        <InboxNotice
          description={t("detail.notFoundDescription")}
          title={t("detail.notFoundTitle")}
          tone="danger"
        />
      </DocumentStateShell>
    );
  }

  const formatDate = (value: string) =>
    format.dateTime(new Date(value), {
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      month: "short",
      year: "numeric",
    });
  const reviewState = getReviewState({
    activeDocument,
    actor,
    detailError,
    formatDate,
    formatNumber: format.number,
    formatStatus: (status) => getReviewStatusLabel(status, review),
    queueDocument: document,
    review,
    reviewError: reviewQuery.isError ? reviewQuery.error : null,
    reviewPending: reviewQuery.isPending,
    reviewResult: reviewQuery.data,
    pipelineHistoryError: pipelineRunsQuery.isError,
    pipelineHistoryPending: pipelineRunsQuery.isPending,
    pipelineRunsCount: pipelineRuns.length,
    latestPipelineRunStatus: latestPipelineRun?.status ?? null,
  });
  const statusLabel = getReviewStatusLabel(activeDocument.status, review);

  return (
    <PageShell
      className="max-w-[1520px]"
      navigation={
        <PageBackLink href={collectionPath}>
          {isArchive ? archive("back") : t("detail.back")}
        </PageBackLink>
      }
    >
      <PageHeader
        actions={
          <div className="flex shrink-0 flex-wrap items-center gap-2">
            {isArchive ? (
              <ArchiveLinkButton archiveUrl={activeDocument.archiveUrl} />
            ) : null}
            {canDelete ? (
              <Button
                onClick={() => setIsDeletionDialogOpen(true)}
                size="sm"
                variant="destructive"
              >
                <Trash2Icon />
                {t("deletion.action")}
              </Button>
            ) : null}
            <Badge
              aria-label={review("statusAria", { status: statusLabel })}
              variant="secondary"
            >
              {statusLabel}
            </Badge>
            <NavigationButton
              basePath={collectionPath}
              direction="previous"
              document={previousDocument}
            />
            <NavigationButton
              basePath={collectionPath}
              direction="next"
              document={nextDocument}
            />
          </div>
        }
        description={review("description")}
        icon={FileCheck2Icon}
        title={activeDocument.originalFilename}
      />

      {isArchive && approvalCompleted ? (
        <InboxNotice
          description={archive("approvalCompleted.description")}
          title={archive("approvalCompleted.title")}
        />
      ) : null}

      <PanelCard className="grid min-h-[40rem] gap-0 overflow-hidden py-0 lg:h-[calc(100vh-15rem)] lg:min-h-[34rem] lg:grid-cols-[minmax(0,58fr)_auto_minmax(360px,42fr)]">
        <InboxPdfViewer document={activeDocument} />
        <Separator className="lg:hidden" />
        <Separator className="hidden lg:block" orientation="vertical" />
        <DocumentWorkspacePanel
          canReview={canReview}
          document={activeDocument}
          formatDate={formatDate}
          formatNumber={format.number}
          formatStatus={(status) => getReviewStatusLabel(status, review)}
          reviewState={reviewState}
          metadataState={{
            isError: metadataSchemaQuery.isError,
            isPending: metadataSchemaQuery.isPending,
            metadataSchema: metadataSchemaQuery.data ?? null,
          }}
          readOnly={isArchive || activeDocument.status === "approved"}
        />
      </PanelCard>
      <DocumentDeletionDialog
        document={activeDocument}
        onDeleted={async () => {
          await queryClient.invalidateQueries({
            queryKey: inboxQueryKeys.documents(),
          });
          router.push(collectionPath);
        }}
        onOpenChange={setIsDeletionDialogOpen}
        open={isDeletionDialogOpen}
      />
    </PageShell>
  );
}

function ArchiveLinkButton({ archiveUrl }: { archiveUrl: string | null }) {
  const archive = useTranslations("Archive");

  if (archiveUrl) {
    return (
      <Button asChild size="sm" variant="ghost">
        <a href={archiveFolderUrl(archiveUrl)} rel="noreferrer" target="_blank">
          <ExternalLinkIcon />
          {archive("sharePoint.openFolder")}
        </a>
      </Button>
    );
  }

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span tabIndex={0}>
          <Button disabled size="sm" variant="ghost">
            <ExternalLinkIcon />
            {archive("sharePoint.openFolder")}
          </Button>
        </span>
      </TooltipTrigger>
      <TooltipContent>{archive("sharePoint.unavailable")}</TooltipContent>
    </Tooltip>
  );
}

interface NavigationButtonProps {
  basePath: "/archive" | "/documents";
  direction: "previous" | "next";
  document: InboxDocument | null;
}

function NavigationButton({
  basePath,
  direction,
  document,
}: NavigationButtonProps) {
  const t = useTranslations("Inbox.detail");
  const review = useTranslations("ReviewWorkspace.navigation");
  const isPrevious = direction === "previous";
  const label = isPrevious ? t("previous") : t("next");
  const ariaLabel = document
    ? isPrevious
      ? review("previousAria", { name: document.name })
      : review("nextAria", { name: document.name })
    : undefined;

  if (!document) {
    return (
      <Button disabled size="sm" variant="ghost">
        {isPrevious ? <ChevronLeftIcon data-icon="inline-start" /> : null}
        {label}
        {!isPrevious ? <ChevronRightIcon data-icon="inline-end" /> : null}
      </Button>
    );
  }

  return (
    <Button asChild size="sm" variant="ghost">
      <Link aria-label={ariaLabel} href={`${basePath}/${document.id}`}>
        {isPrevious ? <ChevronLeftIcon data-icon="inline-start" /> : null}
        {label}
        {!isPrevious ? <ChevronRightIcon data-icon="inline-end" /> : null}
      </Link>
    </Button>
  );
}

function DocumentStateShell({
  children,
  mode,
  title,
}: {
  children: ReactNode;
  mode: "archive" | "inbox";
  title: string;
}) {
  const t = useTranslations("Inbox");
  const archive = useTranslations("Archive");
  const isArchive = mode === "archive";

  return (
    <PageShell
      className="max-w-[960px]"
      navigation={
        <PageBackLink href={isArchive ? "/archive" : "/documents"}>
          {isArchive ? archive("back") : t("detail.back")}
        </PageBackLink>
      }
    >
      <PageHeader
        description={t("detail.description")}
        icon={FileTextIcon}
        title={title}
      />
      {children}
    </PageShell>
  );
}

interface GetReviewStateInput {
  activeDocument: InboxDocument;
  actor: ReturnType<typeof useCurrentActor>["actor"];
  detailError: Error | null;
  formatDate: (value: string) => string;
  formatNumber: (
    value: number,
    options?: { maximumFractionDigits?: number },
  ) => string;
  formatStatus: (status: string) => string;
  queueDocument: InboxDocument;
  review: ReturnType<typeof useTranslations>;
  reviewError: Error | null;
  reviewPending: boolean;
  reviewResult: DocumentReview | undefined;
  pipelineHistoryError: boolean;
  pipelineHistoryPending: boolean;
  pipelineRunsCount: number;
  latestPipelineRunStatus: OcrPipelineRunStatus | null;
}

function getReviewState({
  activeDocument,
  actor,
  detailError,
  review,
  reviewError,
  reviewPending,
  reviewResult,
  pipelineHistoryError,
  pipelineHistoryPending,
  pipelineRunsCount,
  latestPipelineRunStatus,
}: GetReviewStateInput): DocumentReviewState {
  if (detailError || reviewError) {
    return {
      description: review("errors.loadDescription"),
      kind: "error",
      title: review("errors.loadTitle"),
    };
  }

  if (reviewPending || !reviewResult) {
    return { kind: "loading" };
  }

  const presentationKind = getDocumentReviewPresentationKind({
    historyError: pipelineHistoryError,
    historyPending: pipelineHistoryPending,
    latestRunStatus: latestPipelineRunStatus,
    review: reviewResult,
    runCount: pipelineRunsCount,
  });

  if (presentationKind === "loading") {
    return { kind: "loading" };
  }

  if (presentationKind === "not_run") {
    return {
      description: review("notRun.description"),
      kind: "unavailable",
      title: review("notRun.title"),
    };
  }

  if (presentationKind === "unavailable") {
    return {
      description: review("unavailable.description"),
      kind: "unavailable",
      title: review("unavailable.title"),
    };
  }

  return {
    kind: "ready",
    model: buildReviewWorkspaceViewModel({
      actor,
      document: activeDocument,
      review: reviewResult,
    }),
  };
}

function getReviewStatusLabel(
  status: string,
  t: ReturnType<typeof useTranslations>,
): string {
  if (REVIEW_STATUS_LABEL_KEYS.some((knownStatus) => knownStatus === status)) {
    return t(`status.${status as (typeof REVIEW_STATUS_LABEL_KEYS)[number]}`);
  }

  return formatFallbackStatusLabel(status);
}
