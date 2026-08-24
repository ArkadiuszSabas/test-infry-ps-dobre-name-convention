"use client";

import { useTranslations } from "next-intl";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import type {
  OcrPipelineDiagnostic,
  OcrPipelineDiagnosticSeverity,
  OcrPipelineStep,
} from "@/lib/ocr-pipelines/types";
import { getDiagnosticTarget } from "@/lib/ocr-pipelines/diagnostics-view-model";
import { diagnosticBusinessMessageKey } from "@/lib/ocr-pipelines/view-model";

interface PipelineDiagnosticProps {
  diagnostic: OcrPipelineDiagnostic;
  steps: readonly OcrPipelineStep[];
}

export function PipelineDiagnosticNotice({
  diagnostic,
  steps,
}: PipelineDiagnosticProps) {
  const t = useTranslations("AdminOcrPipelines.detail.diagnostics");
  const fieldsT = useTranslations("AdminOcrPipelines.detail.diagnosticFields");
  const messageKey = diagnosticBusinessMessageKey(diagnostic);
  const target = getDiagnosticTarget(diagnostic, steps);
  const targetLabel =
    target.step && target.stepIndex !== null
      ? fieldsT("targetStep", {
          name: target.step.displayName,
          number: target.stepIndex + 1,
        })
      : fieldsT("targetPipeline");
  const detailRows = [
    {
      label: fieldsT("severity"),
      value: fieldsT(`severityValues.${diagnostic.severity}`),
    },
    { label: fieldsT("code"), value: diagnostic.code },
    { label: fieldsT("target"), value: targetLabel },
    diagnostic.stepId
      ? { label: fieldsT("stepId"), value: diagnostic.stepId }
      : null,
    diagnostic.path ? { label: fieldsT("path"), value: diagnostic.path } : null,
    target.fieldPath
      ? { label: fieldsT("control"), value: target.fieldPath }
      : null,
  ].filter((row): row is { label: string; value: string } => Boolean(row));

  return (
    <Alert
      role={diagnostic.severity === "error" ? "alert" : "status"}
      variant={diagnostic.severity === "error" ? "destructive" : "default"}
    >
      <AlertTitle>{t(`${messageKey}.title`)}</AlertTitle>
      <AlertDescription className="space-y-2">
        <p>{diagnostic.message}</p>
        <dl className="grid gap-x-3 gap-y-1 sm:grid-cols-[max-content_minmax(0,1fr)]">
          {detailRows.map((row) => (
            <div className="contents" key={row.label}>
              <dt className="text-xs font-medium text-foreground">
                {row.label}
              </dt>
              <dd className="break-all font-mono text-xs">{row.value}</dd>
            </div>
          ))}
        </dl>
        <p className="text-xs">{t(`${messageKey}.description`)}</p>
      </AlertDescription>
    </Alert>
  );
}

export function StepDiagnosticSummary({
  diagnostic,
  steps,
}: PipelineDiagnosticProps) {
  const fieldsT = useTranslations("AdminOcrPipelines.detail.diagnosticFields");
  const target = getDiagnosticTarget(diagnostic, steps);

  return (
    <div className="rounded-md border bg-background/75 p-2 text-xs">
      <div className="flex flex-wrap items-center gap-2">
        <DiagnosticSeverityBadge severity={diagnostic.severity} />
        <span className="font-medium">{diagnostic.message}</span>
      </div>
      <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-muted-foreground">
        <span>
          {fieldsT("code")}:{" "}
          <span className="font-mono">{diagnostic.code}</span>
        </span>
        {target.fieldPath ? (
          <span>
            {fieldsT("control")}:{" "}
            <span className="font-mono">{target.fieldPath}</span>
          </span>
        ) : null}
        {diagnostic.path ? (
          <span>
            {fieldsT("path")}:{" "}
            <span className="font-mono">{diagnostic.path}</span>
          </span>
        ) : null}
      </div>
    </div>
  );
}

export function DiagnosticSeverityBadge({
  severity,
}: {
  severity: OcrPipelineDiagnosticSeverity;
}) {
  const t = useTranslations(
    "AdminOcrPipelines.detail.diagnosticFields.severityValues",
  );

  return (
    <Badge variant={severity === "error" ? "destructive" : "outline"}>
      {t(severity)}
    </Badge>
  );
}
