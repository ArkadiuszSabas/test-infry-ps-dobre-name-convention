"use client";

import {
  AlertTriangleIcon,
  CheckCircle2Icon,
  FileCode2Icon,
  GitBranchIcon,
  Layers3Icon,
} from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";

import {
  DiagnosticSeverityBadge,
  PipelineDiagnosticNotice,
  StepDiagnosticSummary,
} from "@/components/admin/ocr-pipelines/pipeline-diagnostics";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Notice } from "@/components/ui/notice";
import { PanelCard } from "@/components/ui/panel-card";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { OcrPipelineDetail } from "@/lib/ocr-pipelines/types";
import {
  getDiagnosticsForStep,
  getPipelineLevelDiagnostics,
  mostSevereDiagnostic,
} from "@/lib/ocr-pipelines/diagnostics-view-model";
import {
  canEditOcrPipelineDetail,
  canPublishOcrPipeline,
  detailHasUnpublishedDraftChanges,
  hasBlockingDiagnostics,
  hasPublishReadyValidation,
  pipelineDefinitionForView,
  pipelineDisplayDefinition,
} from "@/lib/ocr-pipelines/view-model";
import { cn } from "@/lib/utils";

interface PipelineDetailPanelProps {
  detail: OcrPipelineDetail | null;
  detailError: string | null;
  isLoading: boolean;
  onEdit: () => void;
  onPublish: () => void;
  onValidate: () => void;
  publishError: string | null;
  publishPending: boolean;
  validateError: string | null;
  validatePending: boolean;
}

export function PipelineDetailPanel({
  detail,
  detailError,
  isLoading,
  onEdit,
  onPublish,
  onValidate,
  publishError,
  publishPending,
  validateError,
  validatePending,
}: PipelineDetailPanelProps) {
  const t = useTranslations("AdminOcrPipelines");
  const [definitionViewState, setDefinitionViewState] = useState<{
    pipelineId: string;
    view: "draft" | "published";
  } | null>(null);

  if (isLoading) {
    return (
      <PanelCard>
        <CardHeader>
          <CardTitle>{t("detail.loadingTitle")}</CardTitle>
          <CardDescription>{t("detail.loadingDescription")}</CardDescription>
        </CardHeader>
      </PanelCard>
    );
  }

  if (!detail) {
    return (
      <PanelCard>
        <CardContent className="p-5">
          <Notice
            title={detailError ?? t("detail.emptyTitle")}
            description={
              detailError
                ? t("detail.loadFailedDescription")
                : t("detail.emptyDescription")
            }
            tone={detailError ? "danger" : "default"}
          />
        </CardContent>
      </PanelCard>
    );
  }

  const definitionView =
    definitionViewState?.pipelineId === detail.id
      ? definitionViewState.view
      : "draft";
  const hasPublishedDraft = Boolean(detail.draft && detail.publishedDefinition);
  const publishedVersion = detail.publishedVersion ?? "?";
  const definition = hasPublishedDraft
    ? pipelineDefinitionForView(detail, definitionView)
    : pipelineDisplayDefinition(detail);
  const diagnostics = detail.lastValidation?.diagnostics ?? [];
  const steps = definition?.steps ?? [];
  const pipelineDiagnostics = getPipelineLevelDiagnostics(diagnostics, steps);
  const orderedDiagnostics = [
    ...pipelineDiagnostics,
    ...diagnostics.filter(
      (diagnostic) => !pipelineDiagnostics.includes(diagnostic),
    ),
  ];
  const hasBlockingValidation = hasBlockingDiagnostics(detail.lastValidation);
  const hasValidation = Boolean(detail.lastValidation);
  const canEdit = canEditOcrPipelineDetail(detail);
  const canPublish = canPublishOcrPipeline(detail);
  const isPublishReady = hasPublishReadyValidation(detail);

  return (
    <PanelCard>
      <CardHeader className="gap-3 px-5">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div className="space-y-1">
            <CardTitle className="flex flex-wrap items-center gap-2 text-base">
              {definition?.name ?? t("detail.unnamed")}
              {detail.isDefault ? <Badge>{t("badges.default")}</Badge> : null}
              <Badge variant="outline">
                {t(`lifecycle.${detail.lifecycle}`)}
              </Badge>
              {detailHasUnpublishedDraftChanges(detail) ? (
                <Badge variant="outline">{t("badges.draftChanges")}</Badge>
              ) : null}
            </CardTitle>
            <CardDescription>
              {definition?.description ?? t("detail.noDescription")}
            </CardDescription>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button
              disabled={!canEdit}
              onClick={onEdit}
              size="sm"
              type="button"
              variant="outline"
            >
              <FileCode2Icon data-icon="inline-start" />
              {t("actions.editDraft")}
            </Button>
            <Button
              disabled={!detail.draft || validatePending}
              onClick={onValidate}
              size="sm"
              type="button"
              variant="secondary"
            >
              <CheckCircle2Icon data-icon="inline-start" />
              {validatePending
                ? t("actions.validating")
                : t("actions.validate")}
            </Button>
            <Button
              disabled={!canPublish || publishPending}
              onClick={onPublish}
              size="sm"
              type="button"
            >
              <GitBranchIcon data-icon="inline-start" />
              {publishPending ? t("actions.publishing") : t("actions.publish")}
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="flex flex-col gap-5 px-5 pb-5">
        {hasPublishedDraft ? (
          <Tabs
            onValueChange={(value) => {
              if (value === "draft" || value === "published") {
                setDefinitionViewState({ pipelineId: detail.id, view: value });
              }
            }}
            value={definitionView}
          >
            <TabsList aria-label={t("detail.definitionViewLabel")}>
              <TabsTrigger value="draft">{t("detail.draftView")}</TabsTrigger>
              <TabsTrigger value="published">
                {t("detail.publishedView", {
                  version: publishedVersion,
                })}
              </TabsTrigger>
            </TabsList>
          </Tabs>
        ) : null}

        {hasPublishedDraft && definitionView === "draft" ? (
          <Notice
            description={t("detail.draftViewDescription", {
              version: publishedVersion,
            })}
            title={t("detail.draftViewTitle")}
          />
        ) : null}
        {hasPublishedDraft && definitionView === "published" ? (
          <Notice
            description={t("detail.publishedViewDescription")}
            title={t("detail.publishedViewTitle", {
              version: publishedVersion,
            })}
          />
        ) : null}

        <div className="grid gap-3 md:grid-cols-3">
          <Metric
            label={t("detail.metrics.steps")}
            value={String(definition?.steps.length ?? 0)}
          />
          <Metric
            label={t("detail.metrics.version")}
            value={
              detail.publishedVersion
                ? t("detail.metrics.versionValue", {
                    version: detail.publishedVersion,
                  })
                : t("detail.metrics.noVersion")
            }
          />
          <Metric
            label={t("detail.metrics.catalog")}
            value={detail.catalogVersion ?? t("detail.metrics.noCatalog")}
          />
        </div>

        {definitionView === "draft" && validateError ? (
          <Notice title={validateError} tone="danger" />
        ) : null}
        {definitionView === "draft" && publishError ? (
          <Notice title={publishError} tone="danger" />
        ) : null}
        {definitionView === "draft" && hasBlockingValidation ? (
          <Notice
            title={t("detail.publishBlockedTitle")}
            description={t("detail.publishBlockedDescription")}
            tone="danger"
          />
        ) : null}
        {definitionView === "draft" && isPublishReady ? (
          <Notice
            title={t("detail.validationReadyTitle")}
            description={t("detail.validationReadyDescription")}
          />
        ) : null}

        {definition ? (
          <section className="space-y-3">
            <h2 className="flex items-center gap-2 text-sm font-semibold">
              <Layers3Icon className="size-4 text-muted-foreground" />
              {t("detail.stepsTitle")}
            </h2>
            <div className="grid gap-2">
              {steps.map((step, index) => {
                const stepDiagnostics = getDiagnosticsForStep(
                  diagnostics,
                  steps,
                  index,
                );
                const severity = mostSevereDiagnostic(stepDiagnostics);

                return (
                  <div
                    className={cn(
                      "grid gap-3 rounded-lg border bg-background p-3 md:grid-cols-[2.25rem_minmax(0,1fr)_auto]",
                      severity === "error" &&
                        "border-destructive/50 bg-destructive/5",
                      severity === "warning" &&
                        "border-primary/30 bg-primary/5",
                    )}
                    key={`${step.stepId}-${index}`}
                  >
                    <span className="flex size-8 items-center justify-center rounded-full bg-muted text-xs font-medium">
                      {index + 1}
                    </span>
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium">
                        {step.displayName}
                      </p>
                      <p className="truncate font-mono text-xs text-muted-foreground">
                        {step.implementationId}
                      </p>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant={step.enabled ? "outline" : "secondary"}>
                        {step.enabled
                          ? t("detail.stepEnabled")
                          : t("detail.stepDisabled")}
                      </Badge>
                      <Badge variant="outline">
                        {t(`failurePolicy.${step.failurePolicy}`)}
                      </Badge>
                      {severity ? (
                        <DiagnosticSeverityBadge severity={severity} />
                      ) : null}
                    </div>
                    {stepDiagnostics.length > 0 ? (
                      <div className="grid gap-2 md:col-start-2 md:col-span-2">
                        {stepDiagnostics.map((diagnostic, diagnosticIndex) => (
                          <StepDiagnosticSummary
                            diagnostic={diagnostic}
                            key={`${diagnostic.code}-${diagnosticIndex}`}
                            steps={steps}
                          />
                        ))}
                      </div>
                    ) : null}
                  </div>
                );
              })}
            </div>
          </section>
        ) : null}

        {definitionView === "draft" ? (
          <section className="space-y-3">
            <h2 className="flex items-center gap-2 text-sm font-semibold">
              <AlertTriangleIcon className="size-4 text-muted-foreground" />
              {t("detail.validationTitle")}
            </h2>
            {orderedDiagnostics.length > 0 ? (
              <div className="grid gap-2">
                {orderedDiagnostics.map((diagnostic, index) => (
                  <PipelineDiagnosticNotice
                    diagnostic={diagnostic}
                    key={`${diagnostic.code}-${index}`}
                    steps={steps}
                  />
                ))}
              </div>
            ) : (
              <Notice
                title={
                  hasValidation
                    ? t("detail.noValidationDiagnosticsTitle")
                    : t("detail.noDiagnosticsTitle")
                }
                description={
                  hasValidation
                    ? t("detail.noValidationDiagnosticsDescription")
                    : t("detail.noDiagnosticsDescription")
                }
              />
            )}
          </section>
        ) : null}
      </CardContent>
    </PanelCard>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border bg-background p-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 truncate text-sm font-semibold">{value}</p>
    </div>
  );
}
