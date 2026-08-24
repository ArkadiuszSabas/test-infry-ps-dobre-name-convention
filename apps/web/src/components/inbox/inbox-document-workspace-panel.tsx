"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FileTextIcon } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState, type ReactNode } from "react";

import { DocumentReviewPanel } from "@/components/inbox/inbox-document-review-panel";
import {
  DocumentParametersSection,
  type DocumentParametersState,
} from "@/components/inbox/inbox-document-parameters";
import { OcrPipelineRunPanel } from "@/components/inbox/ocr-pipeline-run-panel";
import { DocumentTypeDisplaySelect } from "@/components/system-catalogs/document-type-display-select";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { ConfirmActionDialog } from "@/components/ui/confirm-action-dialog";
import { Separator } from "@/components/ui/separator";
import { Spinner } from "@/components/ui/spinner";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useCurrentActor } from "@/hooks/auth/use-current-actor";
import { useCsrfProtectedAction } from "@/hooks/auth/use-csrf-protected-action";
import { isApiError } from "@/lib/api/errors";
import { inboxClient } from "@/lib/inbox/api";
import { inboxQueryKeys } from "@/lib/inbox/query-options";
import type { InboxDocument } from "@/lib/inbox/types";
import { formatFileSize } from "@/lib/inbox/view-model";
import { reviewQueryKeys } from "@/lib/review/query-options";
import type { ReviewWorkspaceViewModel } from "@/lib/review/types";
import { systemCatalogOptionsQueryOptions } from "@/lib/system-catalogs/query-options";

export type DocumentReviewState =
  | {
      kind: "error";
      description: string;
      title: string;
    }
  | {
      kind: "loading";
    }
  | {
      kind: "ready";
      model: ReviewWorkspaceViewModel;
    }
  | {
      kind: "unavailable";
      description: string;
      title: string;
    };

export interface DocumentWorkspacePanelProps {
  canReview: boolean;
  document: InboxDocument;
  formatDate: (value: string) => string;
  formatNumber: (
    value: number,
    options?: { maximumFractionDigits?: number },
  ) => string;
  formatStatus: (status: string) => string;
  reviewState: DocumentReviewState;
  metadataState: DocumentParametersState;
  readOnly?: boolean;
}

export function DocumentWorkspacePanel({
  canReview,
  document,
  formatDate,
  formatNumber,
  formatStatus,
  reviewState,
  metadataState,
  readOnly = false,
}: DocumentWorkspacePanelProps) {
  const t = useTranslations("ReviewWorkspace");

  return (
    <aside
      aria-label={t("workspacePanel.label")}
      className="flex min-h-0 flex-col overflow-hidden bg-background"
    >
      <Tabs
        className="flex min-h-0 flex-1 flex-col gap-0"
        defaultValue={canReview ? "review" : "details"}
        key={canReview ? "review-enabled" : "details-only"}
      >
        <div className="shrink-0 px-4 py-3">
          <TabsList className="w-full" variant="line">
            {canReview ? (
              <TabsTrigger value="review">{t("tabs.review")}</TabsTrigger>
            ) : null}
            <TabsTrigger value="details">{t("tabs.details")}</TabsTrigger>
          </TabsList>
        </div>
        <Separator />

        {canReview ? (
          <TabsContent
            className="min-h-0 flex-1 overflow-hidden data-[state=inactive]:hidden"
            value="review"
          >
            <ReviewTabContent readOnly={readOnly} state={reviewState} />
          </TabsContent>
        ) : null}
        <TabsContent
          className="min-h-0 flex-1 overflow-hidden data-[state=inactive]:hidden"
          value="details"
        >
          <DocumentDetailsPanel
            document={document}
            formatDate={formatDate}
            formatNumber={formatNumber}
            formatStatus={formatStatus}
            metadataState={metadataState}
            readOnly={readOnly}
          />
        </TabsContent>
      </Tabs>
    </aside>
  );
}

function ReviewTabContent({
  readOnly,
  state,
}: {
  readOnly: boolean;
  state: DocumentReviewState;
}) {
  const t = useTranslations("ReviewWorkspace");

  if (state.kind === "ready") {
    return (
      <DocumentReviewPanel
        key={state.model.document.id}
        model={state.model}
        readOnly={readOnly}
      />
    );
  }

  if (state.kind === "loading") {
    return (
      <div className="flex h-full min-h-48 items-center justify-center gap-2 text-sm text-muted-foreground">
        <Spinner className="size-4" />
        {t("loading")}
      </div>
    );
  }

  return (
    <div className="p-4">
      <Alert variant={state.kind === "error" ? "destructive" : "default"}>
        <AlertTitle>{state.title}</AlertTitle>
        <AlertDescription>{state.description}</AlertDescription>
      </Alert>
    </div>
  );
}

function DocumentDetailsPanel({
  document,
  formatDate,
  formatNumber,
  formatStatus,
  metadataState,
  readOnly = false,
}: Omit<DocumentWorkspacePanelProps, "canReview" | "reviewState">) {
  const t = useTranslations("Inbox");

  return (
    <div className="flex h-full min-h-0 flex-col overflow-y-auto bg-background">
      <div className="px-4 py-3">
        <div className="flex items-center gap-2 text-sm font-medium">
          <FileTextIcon className="size-4 text-muted-foreground" />
          {t("detail.panelTitle")}
        </div>
      </div>
      <Separator />

      <Tabs
        className="flex min-h-0 flex-1 flex-col gap-0"
        defaultValue="details"
      >
        <div className="px-4 py-3">
          <TabsList className="w-full" variant="line">
            <TabsTrigger value="details">
              {t("detail.tabs.details")}
            </TabsTrigger>
            <TabsTrigger value="metadata">
              {t("detail.tabs.metadata")}
            </TabsTrigger>
          </TabsList>
        </div>
        <Separator />
        <TabsContent
          className="m-0 min-h-0 flex-1 overflow-y-auto data-[state=inactive]:hidden"
          value="details"
        >
          <div className="flex flex-col gap-5 p-4">
            <OcrPipelineRunPanel
              document={document}
              formatDate={formatDate}
              formatNumber={formatNumber}
              readOnly={readOnly}
            />
          </div>
        </TabsContent>
        <TabsContent
          className="m-0 min-h-0 flex-1 overflow-y-auto data-[state=inactive]:hidden"
          value="metadata"
        >
          <div className="flex flex-col gap-5 p-4">
            <section className="flex flex-col gap-3">
              <h2 className="text-xs font-medium uppercase text-muted-foreground">
                {t("detail.sections.metadata")}
              </h2>
              <dl className="grid grid-cols-[9rem_minmax(0,1fr)] gap-x-4 gap-y-3 text-sm">
                <DetailRow label={t("preview.metadata.type")}>
                  <DocumentTypeChangeControl
                    document={document}
                    readOnly={readOnly}
                  />
                </DetailRow>
                <DetailRow label={t("preview.metadata.status")}>
                  <Badge variant="secondary">
                    {formatStatus(document.status)}
                  </Badge>
                </DetailRow>
                <DetailRow label={t("preview.metadata.size")}>
                  {formatFileSize(
                    document.contentSizeBytes,
                    formatNumber,
                    t("preview.unknownSize"),
                  )}
                </DetailRow>
                <DetailRow label={t("preview.metadata.created")}>
                  {formatDate(document.createdAt)}
                </DetailRow>
              </dl>
            </section>
            <Separator />
            <section className="flex flex-col gap-3">
              <h2 className="text-xs font-medium uppercase text-muted-foreground">
                {t("detail.sections.source")}
              </h2>
              <dl className="grid grid-cols-[9rem_minmax(0,1fr)] gap-x-4 gap-y-3 text-sm">
                <DetailRow label={t("detail.fields.originalFile")}>
                  {document.originalFilename}
                </DetailRow>
                <DetailRow label={t("detail.fields.input")}>
                  {document.connectorName ?? document.connector}
                </DetailRow>
                {document.source === "manual_upload" && document.uploadedBy ? (
                  <DetailRow label={t("detail.fields.uploadedBy")}>
                    <span className="break-all">
                      {document.uploadedBy.displayName}
                    </span>
                  </DetailRow>
                ) : null}
                <DetailRow label={t("detail.fields.documentId")}>
                  <span className="break-all font-mono text-xs">
                    {document.id}
                  </span>
                </DetailRow>
              </dl>
            </section>
            <Separator />
            <DocumentParametersSection
              document={document}
              state={metadataState}
            />
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}

function DocumentTypeChangeControl({
  document,
  readOnly,
}: {
  document: InboxDocument;
  readOnly: boolean;
}) {
  const t = useTranslations("Inbox.documentTypeChange");
  const { actor } = useCurrentActor();
  const queryClient = useQueryClient();
  const csrfAction = useCsrfProtectedAction();
  const [pendingTypeId, setPendingTypeId] = useState<string | null>(null);
  const canReview = Boolean(actor?.permissions.includes("documents.review"));
  const optionsQuery = useQuery(
    systemCatalogOptionsQueryOptions("document_type", canReview),
  );
  const changeMutation = useMutation({
    mutationFn: ({
      confirmImpact,
      documentTypeId,
    }: {
      confirmImpact: boolean;
      documentTypeId: string;
    }) =>
      csrfAction((csrfToken) =>
        inboxClient.changeDocumentType(
          document.id,
          { confirmImpact, documentTypeId },
          { csrfToken },
        ),
      ),
    onSuccess: async () => {
      setPendingTypeId(null);
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: inboxQueryKeys.documentDetail(document.id),
        }),
        queryClient.invalidateQueries({
          queryKey: inboxQueryKeys.documentContext(document.id),
        }),
        queryClient.invalidateQueries({
          queryKey: inboxQueryKeys.documentOcrPipelineRuns(document.id),
        }),
        queryClient.invalidateQueries({
          queryKey: reviewQueryKeys.document(document.id),
        }),
      ]);
    },
  });
  const error = changeMutation.error;
  const requiresConfirmation =
    isApiError(error) &&
    error.code === "DOCUMENT_TYPE_CHANGE_CONFIRMATION_REQUIRED";
  const impact = requiresConfirmation
    ? documentTypeChangeImpact(error.details.impact)
    : null;

  if (!canReview || readOnly)
    return <span>{document.documentTypeName ?? document.documentTypeId}</span>;

  return (
    <div className="space-y-2">
      <DocumentTypeDisplaySelect
        ariaLabel={t("label")}
        definition={optionsQuery.data?.data.definition}
        disabled={
          optionsQuery.isPending ||
          optionsQuery.isError ||
          changeMutation.isPending
        }
        emptyMessage={t("empty")}
        onValueChange={(documentTypeId) => {
          if (documentTypeId !== document.documentTypeId) {
            setPendingTypeId(documentTypeId);
            changeMutation.mutate({ confirmImpact: false, documentTypeId });
          }
        }}
        options={optionsQuery.data?.data.options ?? []}
        placeholder={t("placeholder")}
        searchPlaceholder={t("searchPlaceholder")}
        value={document.documentTypeId}
      />
      {optionsQuery.isError ? (
        <p className="text-sm text-destructive">{t("loadError")}</p>
      ) : null}
      {changeMutation.isError && !requiresConfirmation ? (
        <p className="text-sm text-destructive">
          {isApiError(error) ? error.message : t("saveError")}
        </p>
      ) : null}
      <ConfirmActionDialog
        cancelLabel={t("cancel")}
        confirmLabel={t("confirm")}
        confirmVariant="default"
        description={formatDocumentTypeChangeImpact(
          t("impactDescription"),
          impact,
        )}
        isPending={changeMutation.isPending}
        onConfirm={() =>
          pendingTypeId &&
          changeMutation.mutate({
            confirmImpact: true,
            documentTypeId: pendingTypeId,
          })
        }
        onOpenChange={(open) => {
          if (!open && !changeMutation.isPending) setPendingTypeId(null);
        }}
        open={requiresConfirmation && Boolean(pendingTypeId)}
        title={t("impactTitle")}
      />
    </div>
  );
}

function documentTypeChangeImpact(value: unknown): {
  addedFields: string[];
  removedFields: string[];
  requirednessChangedFields: string[];
} | null {
  if (!value || typeof value !== "object") return null;
  const impact = value as Record<string, unknown>;
  const values = (key: string) =>
    Array.isArray(impact[key]) &&
    impact[key].every((item) => typeof item === "string")
      ? (impact[key] as string[])
      : [];
  return {
    addedFields: values("added_fields"),
    removedFields: values("removed_fields"),
    requirednessChangedFields: values("requiredness_changed_fields"),
  };
}

function formatDocumentTypeChangeImpact(
  description: string,
  impact: ReturnType<typeof documentTypeChangeImpact>,
): string {
  if (!impact) return description;
  const sections = [
    impact.addedFields.length
      ? `Added fields: ${impact.addedFields.join(", ")}`
      : null,
    impact.removedFields.length
      ? `Removed fields: ${impact.removedFields.join(", ")}`
      : null,
    impact.requirednessChangedFields.length
      ? `Requiredness changed: ${impact.requirednessChangedFields.join(", ")}`
      : null,
  ].filter((value): value is string => value !== null);
  return sections.length
    ? `${description}\n\n${sections.join("\n")}`
    : description;
}

interface DetailRowProps {
  children: ReactNode;
  label: string;
}

function DetailRow({ children, label }: DetailRowProps) {
  return (
    <>
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="min-w-0 text-foreground">{children}</dd>
    </>
  );
}
