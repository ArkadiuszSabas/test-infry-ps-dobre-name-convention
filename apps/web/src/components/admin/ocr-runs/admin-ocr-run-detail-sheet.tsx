"use client";

import type { UseQueryResult } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";
import type { ReactNode } from "react";

import { OcrRunStatusBadge } from "@/components/admin/ocr-runs/ocr-run-status-badge";
import { Badge } from "@/components/ui/badge";
import { Notice } from "@/components/ui/notice";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Spinner } from "@/components/ui/spinner";
import type { AdminOcrRunDetailEnvelope } from "@/lib/admin-ocr-runs/types";

interface AdminOcrRunDetailSheetProps {
  onOpenChange: (open: boolean) => void;
  open: boolean;
  query: UseQueryResult<AdminOcrRunDetailEnvelope, Error>;
}

export function AdminOcrRunDetailSheet({
  onOpenChange,
  open,
  query,
}: AdminOcrRunDetailSheetProps) {
  const t = useTranslations("AdminOcrRuns");
  const locale = useLocale();
  const detail = query.data?.data;

  return (
    <Sheet onOpenChange={onOpenChange} open={open}>
      <SheetContent className="sm:max-w-2xl">
        <SheetHeader className="border-b pr-12">
          <SheetTitle>
            {detail?.run.document_name ?? t("detail.title")}
          </SheetTitle>
          <SheetDescription>
            {detail?.run.id ?? t("detail.description")}
          </SheetDescription>
        </SheetHeader>
        <div className="min-h-0 flex-1 space-y-5 overflow-y-auto px-4 pb-6">
          {query.isPending ? (
            <div className="flex items-center gap-2 py-8 text-muted-foreground">
              <Spinner /> {t("loading")}
            </div>
          ) : null}
          {query.isError ? (
            <Notice
              description={t("loadErrorDescription")}
              title={t("loadError")}
              tone="danger"
            />
          ) : null}
          {detail ? (
            <>
              <section className="grid gap-3 rounded-xl border p-4 sm:grid-cols-2">
                <DetailValue label={t("detail.status")}>
                  <OcrRunStatusBadge
                    label={t(`statuses.${detail.run.status}`)}
                    status={detail.run.status}
                  />
                </DetailValue>
                <DetailValue label={t("detail.pipeline")}>
                  {detail.run.pipeline_name ?? detail.run.pipeline_id} · v
                  {detail.run.pipeline_version}
                </DetailValue>
                <DetailValue label={t("detail.created")}>
                  {formatDate(detail.run.created_at, locale)}
                </DetailValue>
                <DetailValue label={t("detail.started")}>
                  {formatOptionalDate(detail.run.started_at, locale)}
                </DetailValue>
                <DetailValue label={t("detail.updated")}>
                  {formatDate(detail.run.updated_at, locale)}
                </DetailValue>
                <DetailValue label={t("detail.completed")}>
                  {formatOptionalDate(detail.run.completed_at, locale)}
                </DetailValue>
                <DetailValue label={t("detail.correlation")}>
                  {detail.run.connector_correlation_id ?? "—"}
                </DetailValue>
                <DetailValue label={t("detail.runId")}>
                  <code className="break-all">{detail.run.id}</code>
                </DetailValue>
              </section>

              <section className="space-y-2">
                <h3 className="font-semibold">{t("detail.steps")}</h3>
                {detail.steps.length ? (
                  detail.steps.map((step) => (
                    <div className="rounded-lg border p-3" key={step.step_id}>
                      <div className="flex items-center justify-between gap-3">
                        <span className="font-medium">{step.display_name}</span>
                        <Badge variant="outline">
                          {t(`stepStatuses.${step.status}`)}
                        </Badge>
                      </div>
                      <p className="mt-1 text-xs text-muted-foreground">
                        {step.step_type} · {step.implementation_id}
                      </p>
                      {step.error ? (
                        <p className="mt-2 text-sm text-destructive">
                          {step.error.code}: {step.error.message}
                        </p>
                      ) : null}
                    </div>
                  ))
                ) : (
                  <p className="text-sm text-muted-foreground">
                    {t("detail.noSteps")}
                  </p>
                )}
              </section>

              <section className="space-y-2">
                <h3 className="font-semibold">{t("detail.metrics")}</h3>
                {Object.entries(detail.metrics).length ? (
                  <dl className="grid gap-2 rounded-lg border p-3 sm:grid-cols-2">
                    {Object.entries(detail.metrics).map(([key, value]) => (
                      <DetailValue key={key} label={key}>
                        {String(value)}
                      </DetailValue>
                    ))}
                  </dl>
                ) : (
                  <p className="text-sm text-muted-foreground">
                    {t("detail.noMetrics")}
                  </p>
                )}
              </section>

              <section className="space-y-2">
                <h3 className="font-semibold">{t("detail.diagnostics")}</h3>
                {detail.error ? (
                  <Notice
                    description={detail.error.message}
                    title={detail.error.code}
                    tone="danger"
                  />
                ) : null}
                {detail.diagnostics.map((diagnostic) => (
                  <Notice
                    description={diagnostic.message}
                    key={`${diagnostic.code}-${diagnostic.step_id ?? "run"}`}
                    title={diagnostic.code}
                    tone={
                      diagnostic.severity === "error" ? "danger" : "default"
                    }
                  />
                ))}
                {!detail.error && !detail.diagnostics.length ? (
                  <p className="text-sm text-muted-foreground">
                    {t("detail.noDiagnostics")}
                  </p>
                ) : null}
              </section>

              <section className="space-y-2">
                <h3 className="font-semibold">{t("detail.attempts")}</h3>
                {detail.attempts.map((attempt) => (
                  <div
                    className="grid gap-1 rounded-lg border p-3 text-sm sm:grid-cols-2"
                    key={attempt.attempt_id}
                  >
                    <span className="font-medium">
                      #{attempt.attempt_number} · {attempt.status}
                    </span>
                    <span>{formatDate(attempt.started_at, locale)}</span>
                    <code className="break-all text-xs text-muted-foreground">
                      {attempt.attempt_id}
                    </code>
                    <span className="text-destructive">
                      {attempt.error_code}
                    </span>
                  </div>
                ))}
                {!detail.attempts.length ? (
                  <p className="text-sm text-muted-foreground">
                    {t("detail.noAttempts")}
                  </p>
                ) : null}
              </section>

              <section className="space-y-2">
                <h3 className="font-semibold">{t("detail.cancellation")}</h3>
                <p className="text-sm text-muted-foreground">
                  {detail.cancellation.requested_at
                    ? `${formatDate(detail.cancellation.requested_at, locale)} · ${detail.cancellation.requested_by_actor_login ?? detail.cancellation.requested_by_actor_id ?? "—"}`
                    : t("detail.noCancellation")}
                </p>
              </section>
            </>
          ) : null}
        </div>
      </SheetContent>
    </Sheet>
  );
}

function DetailValue({
  children,
  label,
}: {
  children: ReactNode;
  label: string;
}) {
  return (
    <div>
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="mt-1">{children}</dd>
    </div>
  );
}

function formatDate(value: string, locale: string): string {
  return new Intl.DateTimeFormat(locale, {
    dateStyle: "medium",
    timeStyle: "medium",
  }).format(new Date(value));
}

function formatOptionalDate(value: string | null, locale: string): string {
  return value ? formatDate(value, locale) : "—";
}
