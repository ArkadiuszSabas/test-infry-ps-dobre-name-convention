"use client";

import { useTranslations } from "next-intl";
import type { ReactNode } from "react";

import { Badge } from "@/components/ui/badge";
import { Spinner } from "@/components/ui/spinner";
import type {
  OcrPipelineRun,
  OcrPipelineRunOcrPageResult,
  OcrPipelineRunResult,
} from "@/lib/inbox/types";

export interface OcrResultSectionProps {
  formatNumber: (
    value: number,
    options?: { maximumFractionDigits?: number },
  ) => string;
  result: OcrPipelineRunResult | null;
  resultError: boolean;
  resultLoading: boolean;
  run: OcrPipelineRun | null;
}
export function OcrResultSection({
  formatNumber,
  result,
  resultError,
  resultLoading,
  run,
}: OcrResultSectionProps) {
  const t = useTranslations("Inbox");
  const ocrResult = result?.result ?? null;

  return (
    <section className="flex flex-col gap-3">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-xs font-medium uppercase text-muted-foreground">
          {t("detail.ocr.title")}
        </h2>
        {run ? <OcrRunStatusBadge run={run} /> : null}
      </div>

      {!run ? (
        <p className="text-sm leading-6 text-muted-foreground">
          {t("detail.ocr.empty")}
        </p>
      ) : null}

      {run && resultLoading ? (
        <InlineLoading label={t("detail.ocr.loadingResult")} />
      ) : null}

      {run && resultError ? (
        <p className="text-sm leading-6 text-destructive">
          {t("detail.ocr.resultLoadFailed")}
        </p>
      ) : null}

      {run && result && !ocrResult ? (
        <p className="text-sm leading-6 text-muted-foreground">
          {result.resultAvailable
            ? t("detail.ocr.availableWithoutPayload")
            : t("detail.ocr.unavailable", {
                reason:
                  result.unavailableReasonCode ??
                  run.resultUnavailableReasonCode ??
                  t("detail.ocr.unknownReason"),
              })}
        </p>
      ) : null}

      {ocrResult ? (
        <div className="flex flex-col gap-4">
          <dl className="grid grid-cols-[9rem_minmax(0,1fr)] gap-x-4 gap-y-2 text-sm">
            <DetailRow label={t("detail.ocr.fields.provider")}>
              <span className="break-all">{ocrResult.providerId}</span>
            </DetailRow>
            <DetailRow label={t("detail.ocr.fields.model")}>
              <span className="break-all">{ocrResult.modelId}</span>
            </DetailRow>
            <DetailRow label={t("detail.ocr.fields.pages")}>
              {t("detail.ocr.pagesSummary", {
                failed: ocrResult.failedPageCount,
                succeeded: ocrResult.succeededPageCount,
                total: ocrResult.totalPageCount,
              })}
            </DetailRow>
            <DetailRow label={t("detail.ocr.fields.confidence")}>
              {formatConfidence(
                ocrResult.averageConfidence,
                formatNumber,
                t("detail.ocr.notAvailable"),
              )}
            </DetailRow>
          </dl>

          {ocrResult.pagesTruncated ? (
            <p className="text-xs leading-5 text-muted-foreground">
              {t("detail.ocr.pagesTruncated")}
            </p>
          ) : null}

          <div className="flex flex-col gap-3">
            {ocrResult.pages.map((page) => (
              <OcrPageResult
                key={page.pageNumber}
                formatNumber={formatNumber}
                page={page}
              />
            ))}
          </div>
        </div>
      ) : null}
    </section>
  );
}

interface OcrRunStatusBadgeProps {
  run: OcrPipelineRun;
}

function OcrRunStatusBadge({ run }: OcrRunStatusBadgeProps) {
  const t = useTranslations("Inbox");
  const variant = run.status === "failed" ? "destructive" : "secondary";

  return <Badge variant={variant}>{ocrRunStatusLabel(run.status, t)}</Badge>;
}

interface OcrPageResultProps {
  page: OcrPipelineRunOcrPageResult;
  formatNumber: (
    value: number,
    options?: { maximumFractionDigits?: number },
  ) => string;
}

function OcrPageResult({ page, formatNumber }: OcrPageResultProps) {
  const t = useTranslations("Inbox");

  return (
    <div className="flex flex-col gap-2 border-t border-border pt-3 first:border-t-0 first:pt-0">
      <div className="flex flex-wrap items-center gap-2 text-sm">
        <span className="font-medium">
          {t("detail.ocr.pageTitle", { page: page.pageNumber })}
        </span>
        <Badge variant="outline">{ocrPageStatusLabel(page.status, t)}</Badge>
        {page.confidence !== null ? (
          <span className="text-xs text-muted-foreground">
            {formatConfidence(
              page.confidence,
              formatNumber,
              t("detail.ocr.notAvailable"),
            )}
          </span>
        ) : null}
      </div>

      {page.warningCodes.length > 0 ? (
        <p className="text-xs leading-5 text-muted-foreground">
          {t("detail.ocr.warningCodes", {
            codes: page.warningCodes.join(", "),
          })}
        </p>
      ) : null}

      {page.errorCode ? (
        <p className="text-xs leading-5 text-destructive">
          {t("detail.ocr.errorCode", { code: page.errorCode })}
        </p>
      ) : null}

      <pre className="max-h-72 overflow-auto whitespace-pre-wrap rounded-sm bg-muted px-3 py-2 font-mono text-xs leading-5 text-foreground">
        {page.text || t("detail.ocr.noText")}
      </pre>

      {page.textTruncated || page.linesTruncated ? (
        <p className="text-xs leading-5 text-muted-foreground">
          {t("detail.ocr.truncated")}
        </p>
      ) : null}
    </div>
  );
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

function InlineLoading({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-2 text-sm text-muted-foreground">
      <Spinner className="size-4" />
      <span>{label}</span>
    </div>
  );
}

function formatConfidence(
  confidence: number | null,
  formatNumber: (
    value: number,
    options?: { maximumFractionDigits?: number },
  ) => string,
  unavailable: string,
) {
  if (confidence === null) {
    return unavailable;
  }

  return `${formatNumber(confidence * 100, { maximumFractionDigits: 1 })}%`;
}

function ocrRunStatusLabel(
  status: OcrPipelineRun["status"],
  t: ReturnType<typeof useTranslations>,
) {
  switch (status) {
    case "pending":
      return t("detail.ocr.runStatus.pending");
    case "running":
      return t("detail.ocr.runStatus.running");
    case "succeeded":
      return t("detail.ocr.runStatus.succeeded");
    case "partial_failed":
      return t("detail.ocr.runStatus.partialFailed");
    case "failed":
      return t("detail.ocr.runStatus.failed");
    default:
      return status;
  }
}

function ocrPageStatusLabel(
  status: string,
  t: ReturnType<typeof useTranslations>,
) {
  switch (status) {
    case "parsed":
      return t("detail.ocr.pageStatus.parsed");
    case "succeeded":
      return t("detail.ocr.pageStatus.succeeded");
    case "failed":
      return t("detail.ocr.pageStatus.failed");
    case "skipped":
      return t("detail.ocr.pageStatus.skipped");
    default:
      return status;
  }
}
