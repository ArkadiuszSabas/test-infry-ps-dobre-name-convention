"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ChevronDownIcon,
  CheckCircle2Icon,
  CircleEllipsisIcon,
  ClipboardCheckIcon,
  Clock3Icon,
  GaugeIcon,
  Loader2Icon,
  PencilIcon,
  PlusIcon,
} from "lucide-react";
import { useFormatter, useTranslations } from "next-intl";
import { useId, useState } from "react";

import { ReviewAddFieldSheet } from "@/components/inbox/review-add-field-sheet";
import { ReviewConfirmationDialogs } from "@/components/inbox/review-confirmation-dialogs";
import { FieldsSection } from "@/components/inbox/review-fields-section";
import { useUnsavedChangesRegistration } from "@/components/system-catalogs/unsaved-changes-provider";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { Textarea } from "@/components/ui/textarea";
import { useCsrfProtectedAction } from "@/hooks/auth/use-csrf-protected-action";
import { useRouter } from "@/i18n/navigation";
import { isApiError } from "@/lib/api/errors";
import { reviewConfidenceColorSettingsQueryOptions } from "@/lib/confidence-colors/query-options";
import { DEFAULT_CONFIDENCE_COLOR_BANDS } from "@/lib/confidence-colors/types";
import { inboxQueryKeys } from "@/lib/inbox/query-options";
import {
  addManualDraftField,
  createReviewDraft,
  createReviewEditSession,
  isDraftDirty,
  removeDraftField,
  toSaveFields,
  updateDraftValue,
  type ManualFieldInput,
} from "@/lib/review/editor-state";
import { sortReviewFieldsByDocumentLocation } from "@/lib/review/field-list";
import { reviewClient } from "@/lib/review/api";
import { reviewQueryKeys } from "@/lib/review/query-options";
import { getBlockingRequiredFieldIds } from "@/lib/review/field-presentation";
import {
  canCurrentActorDecide,
  getApprovalPresentation,
  reviewerDisplayLabel,
} from "@/lib/review/approval-presentation";
import type {
  DocumentReview,
  ReviewFieldItem,
  ReviewSourceSelection,
  ReviewWorkspaceViewModel,
} from "@/lib/review/types";
import { cn } from "@/lib/utils";

type ReviewFilter = "all" | "errors" | "unverified";

export interface DocumentReviewPanelProps {
  model: ReviewWorkspaceViewModel;
  onReviewSourceCleared: () => void;
  onReviewSourceSelected: (selection: ReviewSourceSelection) => void;
  readOnly?: boolean;
}

export function DocumentReviewPanel({
  model,
  onReviewSourceCleared,
  onReviewSourceSelected,
  readOnly = false,
}: DocumentReviewPanelProps) {
  const t = useTranslations("ReviewWorkspace");
  const queryClient = useQueryClient();
  const runCsrfProtectedAction = useCsrfProtectedAction();
  const confidenceColorsQuery = useQuery(
    reviewConfidenceColorSettingsQueryOptions(),
  );
  const [editing, setEditing] = useState(false);
  const [editSession, setEditSession] = useState(() =>
    createReviewEditSession(model.fields, model.version),
  );
  const draft = editSession.fields;
  const [filter, setFilter] = useState<ReviewFilter>("all");
  const [addOpen, setAddOpen] = useState(false);
  const [cancelOpen, setCancelOpen] = useState(false);
  const [conflictReview, setConflictReview] = useState<DocumentReview | null>(
    null,
  );
  const [removeId, setRemoveId] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const unsavedChangesId = useId();

  const saveMutation = useMutation({
    mutationFn: () =>
      runCsrfProtectedAction((csrfToken) =>
        reviewClient.saveDocumentReview(
          model.document.id,
          {
            expectedVersion: editSession.expectedVersion,
            fields: toSaveFields(draft),
          },
          { csrfToken },
        ),
      ),
    onError: async (error) => {
      if (
        isApiError(error) &&
        error.code === "DOCUMENT_REVIEW_VERSION_CONFLICT"
      ) {
        setSaveError(null);
        try {
          const refreshedReview = await reviewClient.getDocumentReview(
            model.document.id,
          );
          if (refreshedReview.version === editSession.expectedVersion) {
            setSaveError(t("errors.conflictRefreshDescription"));
            return;
          }
          queryClient.setQueryData(
            reviewQueryKeys.document(model.document.id),
            refreshedReview,
          );
          await invalidateDocumentCaches(queryClient, model.document.id);
          setConflictReview(refreshedReview);
        } catch {
          setSaveError(t("errors.conflictRefreshDescription"));
        }
        return;
      }
      setSaveError(t("errors.saveDescription"));
    },
    onSuccess: async (saved) => {
      queryClient.setQueryData(
        reviewQueryKeys.document(model.document.id),
        saved,
      );
      setEditSession(createReviewEditSession(saved.fields, saved.version));
      setEditing(false);
      setSaveError(null);
      await invalidateDocumentCaches(queryClient, model.document.id);
    },
  });

  const activeFields = sortReviewFieldsByDocumentLocation(
    editing ? draft : createReviewDraft(model.fields),
  );
  const visibleFields = activeFields.filter((field) =>
    matchesFilter(field, filter),
  );
  const errorCount = activeFields.filter(isProblemField).length;
  const dirty = isDraftDirty(model.fields, draft);
  const canEdit = model.canEditReview && !readOnly;
  useUnsavedChangesRegistration(unsavedChangesId, dirty);

  function startEditing() {
    if (!canEdit) return;
    onReviewSourceCleared();
    setEditSession(createReviewEditSession(model.fields, model.version));
    setEditing(true);
    setSaveError(null);
  }

  function requestCancel() {
    if (dirty) setCancelOpen(true);
    else setEditing(false);
  }

  function discardChanges() {
    setEditSession(createReviewEditSession(model.fields, model.version));
    setEditing(false);
    setCancelOpen(false);
    setSaveError(null);
  }

  function reloadAfterConflict() {
    if (!conflictReview) return;
    setEditSession(
      createReviewEditSession(conflictReview.fields, conflictReview.version),
    );
    setEditing(false);
    setConflictReview(null);
    setSaveError(null);
  }

  function addField(input: ManualFieldInput) {
    setEditSession((current) => ({
      ...current,
      fields: addManualDraftField(current.fields, input, crypto.randomUUID()),
    }));
  }

  return (
    <div
      aria-label={t("panel.label")}
      className="flex h-full min-h-0 flex-col overflow-hidden bg-background"
      data-editing={editing || undefined}
    >
      <div className="flex min-h-0 flex-1 flex-col overflow-y-auto">
        <QualitySection
          errorCount={errorCount}
          onShowErrors={() => setFilter("errors")}
          qualityScore={model.qualityScore}
        />
        <ReviewSeparator />
        <ApprovalSection editing={editing} model={model} readOnly={readOnly} />
        <ReviewSeparator />
        <ReviewControlsSection
          canEdit={canEdit}
          editing={editing}
          filter={filter}
          onEdit={startEditing}
          onFilterChange={setFilter}
        />
        <ReviewSeparator />
        <FieldsSection
          canEdit={canEdit}
          confidenceColorBands={
            confidenceColorsQuery.data?.bands ?? DEFAULT_CONFIDENCE_COLOR_BANDS
          }
          editing={editing}
          fields={visibleFields}
          filtered={filter !== "all"}
          key={model.document.id}
          onChange={(clientId, value) =>
            setEditSession((current) => ({
              ...current,
              fields: updateDraftValue(current.fields, clientId, value),
            }))
          }
          onEdit={startEditing}
          onRemove={setRemoveId}
          onSelectSource={onReviewSourceSelected}
        />
      </div>

      {editing ? (
        <div className="shrink-0 space-y-2 border-t bg-background px-4 py-3 shadow-[0_-4px_12px_rgb(0_0_0/0.04)]">
          {saveError ? (
            <p className="text-sm font-medium text-destructive" role="alert">
              {saveError}
            </p>
          ) : null}
          <div className="flex flex-wrap items-center justify-between gap-2">
            <Button
              onClick={() => setAddOpen(true)}
              type="button"
              variant="outline"
            >
              <PlusIcon />
              {t("fields.add")}
            </Button>
            <div className="flex gap-2">
              <Button onClick={requestCancel} type="button" variant="ghost">
                {t("fields.cancel")}
              </Button>
              <Button
                disabled={!dirty || saveMutation.isPending}
                onClick={() => saveMutation.mutate()}
                type="button"
              >
                {saveMutation.isPending ? t("fields.saving") : t("fields.save")}
              </Button>
            </div>
          </div>
        </div>
      ) : null}

      <ReviewAddFieldSheet
        onAdd={addField}
        onOpenChange={setAddOpen}
        open={addOpen}
      />
      <ReviewConfirmationDialogs
        cancelOpen={cancelOpen}
        conflictOpen={Boolean(conflictReview)}
        conflictUpdatedAt={conflictReview?.updatedAt ?? null}
        conflictUpdatedByActorId={conflictReview?.updatedByActorId ?? null}
        onCancelOpenChange={setCancelOpen}
        onConflictOpenChange={(open) => {
          if (!open) setConflictReview(null);
        }}
        onConflictReload={reloadAfterConflict}
        onDiscard={discardChanges}
        onRemove={() => {
          if (removeId) {
            setEditSession((current) => ({
              ...current,
              fields: removeDraftField(current.fields, removeId),
            }));
            onReviewSourceCleared();
          }
          setRemoveId(null);
        }}
        onRemoveOpenChange={(open) => {
          if (!open) setRemoveId(null);
        }}
        removeOpen={Boolean(removeId)}
      />
    </div>
  );
}

function ReviewControlsSection({
  canEdit,
  editing,
  filter,
  onEdit,
  onFilterChange,
}: {
  canEdit: boolean;
  editing: boolean;
  filter: ReviewFilter;
  onEdit: () => void;
  onFilterChange: (filter: ReviewFilter) => void;
}) {
  const t = useTranslations("ReviewWorkspace");

  return (
    <section
      className={cn(
        "flex shrink-0 items-center justify-between gap-3 px-4 py-3",
        editing && "bg-primary/10 shadow-[inset_3px_0_0_var(--primary)]",
      )}
      data-section="review-controls"
    >
      <div className="flex min-w-0 items-start gap-2">
        <ClipboardCheckIcon
          className={cn(
            "mt-0.5 size-4 shrink-0 text-muted-foreground",
            editing && "text-primary",
          )}
        />
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="text-sm font-semibold">{t("panel.title")}</h2>
            {editing ? (
              <Badge variant="default">{t("panel.editingBadge")}</Badge>
            ) : null}
          </div>
          <p className="text-xs text-muted-foreground">
            {editing ? t("panel.editDescription") : t("panel.description")}
          </p>
        </div>
      </div>
      <div className="flex shrink-0 items-center gap-2">
        <Select
          onValueChange={(value) => onFilterChange(toReviewFilter(value))}
          value={filter}
        >
          <SelectTrigger aria-label={t("fields.filterAria")} className="w-36">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">{t("fields.filters.all")}</SelectItem>
            <SelectItem value="errors">{t("fields.filters.errors")}</SelectItem>
            <SelectItem value="unverified">
              {t("fields.filters.unverified")}
            </SelectItem>
          </SelectContent>
        </Select>
        {!editing && canEdit ? (
          <Button onClick={onEdit} size="sm" type="button" variant="outline">
            <PencilIcon />
            {t("fields.edit")}
          </Button>
        ) : null}
      </div>
    </section>
  );
}

function QualitySection({
  errorCount,
  onShowErrors,
  qualityScore,
}: {
  errorCount: number;
  onShowErrors: () => void;
  qualityScore: number | null;
}) {
  const t = useTranslations("ReviewWorkspace.quality");
  const score = qualityScore === null ? null : Math.round(qualityScore * 100);
  return (
    <section className="shrink-0 px-4 py-3" data-section="quality">
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-start gap-2">
          <GaugeIcon className="mt-0.5 size-4 shrink-0 text-primary" />
          <div>
            <h2 className="text-sm font-semibold">{t("title")}</h2>
            <p className="text-xs text-muted-foreground">{t("description")}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button
            onClick={onShowErrors}
            size="sm"
            type="button"
            variant="ghost"
          >
            {t("errors", { count: errorCount })}
          </Button>
          <Badge variant="secondary">
            {score === null ? t("unavailable") : t("score", { score })}
          </Badge>
        </div>
      </div>
      {score !== null ? <Progress className="mt-3 h-2" value={score} /> : null}
    </section>
  );
}

function ApprovalSection({
  editing,
  model,
  readOnly,
}: {
  editing: boolean;
  model: ReviewWorkspaceViewModel;
  readOnly: boolean;
}) {
  const t = useTranslations("ReviewWorkspace.approval");
  const format = useFormatter();
  const queryClient = useQueryClient();
  const router = useRouter();
  const runCsrfProtectedAction = useCsrfProtectedAction();
  const [comment, setComment] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [approvalOutcomeUnknown, setApprovalOutcomeUnknown] = useState(false);
  const [checkingFinalApproval, setCheckingFinalApproval] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  const detailsId = useId();
  const historyId = useId();
  const approval = model.approval;
  const expectedReviewVersion = model.version;
  const blockingRequiredFieldCount = getBlockingRequiredFieldIds(
    model.fields,
  ).length;
  const canDecide =
    !readOnly &&
    expectedReviewVersion !== null &&
    canCurrentActorDecide(approval, model.isActiveVerifier);
  const presentation = getApprovalPresentation(approval);
  const singleReviewerWorkflow = presentation.totalCount === 1;
  const approvalTitle = t(singleReviewerWorkflow ? "titleSingle" : "title");
  const isFinalApproval =
    presentation.totalCount > 0 &&
    presentation.approvedCount === presentation.totalCount - 1;
  const decisionMutation = useMutation({
    mutationFn: (decision: "approve" | "reject") => {
      if (expectedReviewVersion === null) {
        throw new Error("Approval requires a persisted Review version.");
      }
      return runCsrfProtectedAction((csrfToken) =>
        reviewClient.decideApproval(
          model.document.id,
          decision,
          comment.trim() || null,
          expectedReviewVersion,
          { csrfToken },
        ),
      );
    },
    onMutate: () => {
      setApprovalOutcomeUnknown(false);
      setError(null);
    },
    onSuccess: async (updatedReview, decision) => {
      setComment("");
      setError(null);

      queryClient.setQueryData(
        reviewQueryKeys.document(model.document.id),
        updatedReview,
      );

      if (updatedReview.approval?.status === "approved") {
        await openFinalApprovalInArchive(updatedReview);
        return;
      }

      if (decision === "approve" && isFinalApproval) {
        setError(t("finalizationNotSaved"));
      }

      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: reviewQueryKeys.document(model.document.id),
        }),
        queryClient.invalidateQueries({
          queryKey: inboxQueryKeys.documentDetail(model.document.id),
        }),
        queryClient.invalidateQueries({
          queryKey: inboxQueryKeys.documentList(),
        }),
        queryClient.invalidateQueries({
          queryKey: inboxQueryKeys.documentList(true),
        }),
      ]);
    },
    onError: async (reason, decision) => {
      if (
        isApiError(reason) &&
        reason.code === "DOCUMENT_APPROVAL_REVIEW_VERSION_CONFLICT"
      ) {
        try {
          const refreshedReview = await reviewClient.getDocumentReview(
            model.document.id,
          );
          if (
            refreshedReview.version === null ||
            refreshedReview.version === expectedReviewVersion
          ) {
            setError(t("versionConflictRefreshFailed"));
            return;
          }
          queryClient.setQueryData(
            reviewQueryKeys.document(model.document.id),
            refreshedReview,
          );
          await invalidateDocumentCaches(queryClient, model.document.id);
          setError(t("versionConflict"));
        } catch {
          setError(t("versionConflictRefreshFailed"));
        }
        return;
      }

      if (
        decision === "approve" &&
        isFinalApproval &&
        isAmbiguousApprovalError(reason)
      ) {
        await reconcileFinalApproval();
        return;
      }

      setError(reason instanceof Error ? reason.message : t("error"));
    },
  });
  const finalApprovalPending =
    isFinalApproval &&
    decisionMutation.isPending &&
    decisionMutation.variables === "approve";
  const decisionInteractionPending =
    decisionMutation.isPending || checkingFinalApproval;
  const rejectDisabled =
    decisionInteractionPending ||
    approvalOutcomeUnknown ||
    comment.trim().length === 0;

  async function openFinalApprovalInArchive(updatedReview: DocumentReview) {
    setApprovalOutcomeUnknown(false);
    queryClient.setQueryData(
      reviewQueryKeys.document(model.document.id),
      updatedReview,
    );
    await Promise.all([
      queryClient.invalidateQueries({
        queryKey: reviewQueryKeys.document(model.document.id),
        refetchType: "none",
      }),
      queryClient.invalidateQueries({
        queryKey: inboxQueryKeys.documentDetail(model.document.id),
        refetchType: "none",
      }),
      queryClient.invalidateQueries({
        queryKey: inboxQueryKeys.documentList(),
        refetchType: "none",
      }),
      queryClient.invalidateQueries({
        queryKey: inboxQueryKeys.documentList(true),
        refetchType: "none",
      }),
    ]);
    router.replace(`/archive/${model.document.id}?approval=completed`);
  }

  async function reconcileFinalApproval() {
    setCheckingFinalApproval(true);
    setError(null);

    try {
      const refreshedReview = await reviewClient.getDocumentReview(
        model.document.id,
      );
      queryClient.setQueryData(
        reviewQueryKeys.document(model.document.id),
        refreshedReview,
      );

      if (refreshedReview.approval?.status === "approved") {
        await openFinalApprovalInArchive(refreshedReview);
        return;
      }

      setApprovalOutcomeUnknown(false);
      await invalidateDocumentCaches(queryClient, model.document.id);
      setError(t("finalizationNotSaved"));
    } catch {
      setApprovalOutcomeUnknown(true);
      setError(t("finalizationUnknown"));
    } finally {
      setCheckingFinalApproval(false);
    }
  }

  return (
    <section
      aria-label={approvalTitle}
      className="shrink-0"
      data-section="approval"
      data-state={isOpen ? "expanded" : "collapsed"}
    >
      <button
        aria-controls={detailsId}
        aria-expanded={isOpen}
        aria-label={t(
          isOpen
            ? singleReviewerWorkflow
              ? "collapseSingle"
              : "collapse"
            : singleReviewerWorkflow
              ? "expandSingle"
              : "expand",
        )}
        className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left"
        onClick={() => setIsOpen((current) => !current)}
        type="button"
      >
        <div className="flex min-w-0 items-center gap-2">
          <CircleEllipsisIcon className="size-4 shrink-0 text-muted-foreground" />
          <span className="text-sm font-semibold">{approvalTitle}</span>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <Badge className={approvalStatusClassName(presentation.status)}>
            {t(`statuses.${presentation.status}`, {
              approved: presentation.approvedCount,
              total: presentation.totalCount,
            })}
          </Badge>
          <ChevronDownIcon
            aria-hidden="true"
            className={cn(
              "size-4 text-muted-foreground transition-transform",
              isOpen && "rotate-180",
            )}
          />
        </div>
      </button>
      {isOpen ? (
        <div className="px-4 pb-3" id={detailsId}>
          {approval ? (
            <ol className="space-y-2" aria-label={t("steps")}>
              {approval.steps.map((step) => {
                const isApproved = step.status === "approved";
                const StatusIcon = isApproved ? CheckCircle2Icon : Clock3Icon;
                const statusLabel = t(`stepStatuses.${step.status}`);

                return (
                  <li
                    className={cn(
                      "min-w-0 rounded-md border-l-2 border-y border-r border-border/70 p-3 text-xs",
                      isApproved
                        ? "border-l-emerald-500"
                        : "border-l-orange-500",
                    )}
                    key={step.number}
                  >
                    <div className="flex min-w-0 gap-2">
                      <StatusIcon
                        aria-label={statusLabel}
                        className={cn(
                          "mt-0.5 size-4 shrink-0",
                          isApproved ? "text-emerald-600" : "text-orange-600",
                        )}
                        role="img"
                      />
                      <div className="min-w-0 flex-1">
                        <div className="flex min-w-0 flex-wrap items-baseline gap-x-1.5 gap-y-0.5">
                          <span
                            className={cn(
                              "font-semibold",
                              isApproved
                                ? "text-emerald-700"
                                : "text-orange-700",
                            )}
                          >
                            {statusLabel}
                          </span>
                          <span className="text-muted-foreground">
                            · {t("step", { number: step.number })}
                          </span>
                        </div>
                        {isApproved ? (
                          <p className="mt-1 break-words text-muted-foreground">
                            {reviewerDisplayLabel(
                              step.reviewerDisplayName,
                              t("unassigned"),
                            )}
                            {step.decidedAt
                              ? ` · ${formatApprovalDate(format, step.decidedAt)}`
                              : ""}
                          </p>
                        ) : (
                          <p className="mt-1 break-words text-muted-foreground">
                            {t("unassignedDifferentReviewer")}
                          </p>
                        )}
                        {step.comment ? (
                          <div className="mt-2 break-words bg-muted/50 px-3 py-2 text-foreground">
                            <p className="text-[0.6875rem] font-medium text-muted-foreground">
                              {t("commentLabel")}
                            </p>
                            <p className="mt-0.5 whitespace-pre-wrap">
                              {step.comment}
                            </p>
                          </div>
                        ) : null}
                      </div>
                    </div>
                  </li>
                );
              })}
            </ol>
          ) : null}
          {canDecide ? (
            <div className="mt-3 space-y-2">
              <Textarea
                aria-label={t("comment")}
                disabled={
                  editing ||
                  decisionInteractionPending ||
                  approvalOutcomeUnknown
                }
                onChange={(event) => setComment(event.target.value)}
                placeholder={t("commentPlaceholder")}
                value={comment}
              />
              {finalApprovalPending || checkingFinalApproval ? (
                <p aria-live="polite" className="text-xs text-muted-foreground">
                  {t(
                    checkingFinalApproval
                      ? "checkingFinalization"
                      : "finalizing",
                  )}
                </p>
              ) : null}
              {error ? (
                <div className="space-y-2">
                  <p className="text-xs text-destructive">{error}</p>
                  {approvalOutcomeUnknown ? (
                    <Button
                      onClick={() => void reconcileFinalApproval()}
                      size="sm"
                      type="button"
                      variant="outline"
                    >
                      {t("checkStatus")}
                    </Button>
                  ) : null}
                </div>
              ) : null}
              <div className="flex gap-2">
                <Button
                  aria-busy={finalApprovalPending || undefined}
                  disabled={
                    editing ||
                    decisionInteractionPending ||
                    approvalOutcomeUnknown ||
                    blockingRequiredFieldCount > 0
                  }
                  onClick={() => decisionMutation.mutate("approve")}
                  size="sm"
                >
                  {finalApprovalPending ? (
                    <Loader2Icon
                      aria-hidden="true"
                      className="animate-spin"
                      data-icon="inline-start"
                    />
                  ) : null}
                  {t(
                    finalApprovalPending
                      ? "finalizing"
                      : isFinalApproval
                        ? "approveFinal"
                        : "approve",
                  )}
                </Button>
                <Button
                  disabled={editing || rejectDisabled}
                  onClick={() => decisionMutation.mutate("reject")}
                  size="sm"
                  variant="destructive"
                >
                  {t("reject")}
                </Button>
              </div>
              <p className="text-xs text-muted-foreground">
                {editing
                  ? t("editingBlocked")
                  : blockingRequiredFieldCount > 0
                    ? t("missingRequiredBlocked", {
                        count: blockingRequiredFieldCount,
                      })
                    : t("rejectHint")}
              </p>
            </div>
          ) : null}
          {approval?.history.length ? (
            <div className="mt-3 border-t pt-3">
              <button
                aria-controls={historyId}
                aria-expanded={isHistoryOpen}
                className="flex w-full items-center gap-2 text-left text-xs font-medium"
                onClick={() => setIsHistoryOpen((current) => !current)}
                type="button"
              >
                <ChevronDownIcon
                  aria-hidden="true"
                  className={cn(
                    "size-4 text-muted-foreground transition-transform",
                    isHistoryOpen && "rotate-180",
                  )}
                />
                <span>{t("history")}</span>
                <span className="text-muted-foreground">
                  {t("historyCount", { count: approval.history.length })}
                </span>
              </button>
              {isHistoryOpen ? (
                <ol
                  className="mt-3 space-y-3 border-l border-border pl-3 text-xs"
                  id={historyId}
                >
                  {approval.history.map((item) => {
                    const decisionLabel = t(
                      `historyDecisions.${item.decision}`,
                    );
                    const isApproved = item.decision === "approved";
                    const StatusIcon = isApproved
                      ? CheckCircle2Icon
                      : Clock3Icon;

                    return (
                      <li
                        className={cn(
                          "relative min-w-0 before:absolute before:-left-[1.05rem] before:top-1 before:size-2 before:rounded-full",
                          isApproved
                            ? "before:bg-emerald-600"
                            : "before:bg-red-600",
                        )}
                        key={`${item.runNumber}-${item.stepNumber}-${item.decidedAt}`}
                      >
                        <div className="flex min-w-0 gap-2">
                          <StatusIcon
                            aria-label={decisionLabel}
                            className={cn(
                              "mt-0.5 size-4 shrink-0",
                              isApproved ? "text-emerald-600" : "text-red-600",
                            )}
                            role="img"
                          />
                          <div className="min-w-0 flex-1">
                            <p className="break-words font-medium">
                              {decisionLabel}
                              <span className="font-normal text-muted-foreground">
                                {` · ${t("step", { number: item.stepNumber })}`}
                              </span>
                            </p>
                            <p className="mt-0.5 break-words text-muted-foreground">
                              {reviewerDisplayLabel(
                                item.actorDisplayName,
                                t("unassigned"),
                              )}
                              {` · ${formatApprovalDate(format, item.decidedAt)}`}
                            </p>
                            <div className="mt-2 break-words bg-muted/50 px-3 py-2 text-foreground">
                              <p className="text-[0.6875rem] font-medium text-muted-foreground">
                                {t("commentLabel")}
                              </p>
                              <p className="mt-0.5 whitespace-pre-wrap">
                                {item.comment ?? t("noComment")}
                              </p>
                            </div>
                          </div>
                        </div>
                      </li>
                    );
                  })}
                </ol>
              ) : null}
            </div>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}

function formatApprovalDate(
  format: ReturnType<typeof useFormatter>,
  decidedAt: string,
): string {
  return format.dateTime(new Date(decidedAt), {
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    month: "short",
    year: "numeric",
  });
}

function approvalStatusClassName(
  status: ReturnType<typeof getApprovalPresentation>["status"],
): string {
  switch (status) {
    case "approved":
      return "border-emerald-200 bg-emerald-50 text-emerald-700";
    case "inReview":
      return "border-orange-200 bg-orange-50 text-orange-700";
    case "rejected":
      return "border-red-200 bg-red-50 text-red-700";
    case "pending":
      return "border-slate-200 bg-slate-100 text-slate-700";
  }
}

function isAmbiguousApprovalError(error: unknown): boolean {
  return !isApiError(error) || error.status >= 500;
}

function invalidateDocumentCaches(
  queryClient: ReturnType<typeof useQueryClient>,
  documentId: string,
) {
  return Promise.all([
    queryClient.invalidateQueries({
      queryKey: inboxQueryKeys.documentDetail(documentId),
    }),
    queryClient.invalidateQueries({
      queryKey: inboxQueryKeys.documentList(),
    }),
    queryClient.invalidateQueries({
      queryKey: inboxQueryKeys.documentList(true),
    }),
  ]);
}

function isProblemField(field: ReviewFieldItem): boolean {
  return (
    field.requiresReview ||
    field.validations.some((validation) => validation.severity === "error") ||
    ["conflicting", "missing", "uncertain"].includes(field.status)
  );
}

function matchesFilter(field: ReviewFieldItem, filter: ReviewFilter): boolean {
  if (filter === "errors") return isProblemField(field);
  if (filter === "unverified") {
    return field.status === "unidentified" || field.validations.length === 0;
  }
  return true;
}

function toReviewFilter(value: string): ReviewFilter {
  return value === "errors" || value === "unverified" ? value : "all";
}

function ReviewSeparator() {
  return <Separator className="shrink-0" />;
}
