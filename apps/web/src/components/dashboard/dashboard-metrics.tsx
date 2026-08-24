"use client";

import { ArchiveIcon } from "lucide-react";
import { useFormatter, useTranslations } from "next-intl";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Link } from "@/i18n/navigation";
import type {
  DashboardOverview,
  DashboardWindowDays,
} from "@/lib/dashboard/types";

export function OcrTimingCard({
  timing,
  windowDays,
}: {
  timing: DashboardOverview["ocrTiming"];
  windowDays: DashboardWindowDays;
}) {
  const t = useTranslations("Dashboard");
  const format = useFormatter();
  const { averageSeconds, maxSeconds, minSeconds } = timing;

  if (averageSeconds === null || minSeconds === null || maxSeconds === null) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>{t("ocrTiming.title")}</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            {t("ocrTiming.empty")}
          </p>
        </CardContent>
      </Card>
    );
  }

  const range = maxSeconds - minSeconds;
  const averagePosition =
    range === 0 ? 50 : ((averageSeconds - minSeconds) / range) * 100;
  const seconds = (value: number) =>
    format.number(value, {
      maximumFractionDigits: 1,
      minimumFractionDigits: 1,
    });

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("ocrTiming.title")}</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-4">
        <p>
          <span className="text-sm text-muted-foreground">
            {t("ocrTiming.averageLabel")}{" "}
          </span>
          <span className="text-2xl font-semibold tabular-nums">
            {t("ocrTiming.seconds", { value: seconds(averageSeconds) })}
          </span>
        </p>
        <div
          aria-label={t("ocrTiming.rangeAria", {
            average: seconds(averageSeconds),
            maximum: seconds(maxSeconds),
            minimum: seconds(minSeconds),
          })}
          className="grid gap-2"
          role="img"
        >
          <div className="relative h-1 rounded-full bg-border">
            <span
              className="absolute top-1/2 size-3 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-background bg-primary shadow"
              style={{ left: `${averagePosition}%` }}
            />
          </div>
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>
              {t("ocrTiming.minimum", {
                value: seconds(minSeconds),
              })}
            </span>
            <span>
              {t("ocrTiming.average", {
                value: seconds(averageSeconds),
              })}
            </span>
            <span>
              {t("ocrTiming.maximum", {
                value: seconds(maxSeconds),
              })}
            </span>
          </div>
        </div>
        <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
          <span>
            {t("ocrTiming.samples", {
              count: timing.successfulSampleCount,
              days: windowDays,
            })}
          </span>
          {timing.weightedAverageSecondsPerPage !== null ? (
            <Badge variant="secondary">
              {t("ocrTiming.perPage", {
                value: seconds(timing.weightedAverageSecondsPerPage),
              })}
            </Badge>
          ) : null}
        </div>
      </CardContent>
    </Card>
  );
}

export function ArchiveSummaryCard({
  total,
  addedInWindow,
  windowDays,
}: {
  total: number;
  addedInWindow: number;
  windowDays: DashboardWindowDays;
}) {
  const t = useTranslations("Dashboard");
  const format = useFormatter();

  return (
    <Card>
      <CardContent className="flex items-end justify-between gap-4 py-5">
        <div>
          <div className="flex items-center gap-2">
            <ArchiveIcon aria-hidden="true" className="size-4 text-primary" />
            <h2 className="font-medium">{t("archiveSummary.title")}</h2>
          </div>
          <div className="mt-2 flex flex-wrap items-baseline gap-3">
            <span className="text-3xl font-semibold tabular-nums">
              {format.number(total)}
            </span>
            <span className="text-xs text-emerald-600">
              {t("archiveSummary.added", {
                count: addedInWindow,
                days: windowDays,
              })}
            </span>
          </div>
        </div>
        <Button asChild size="sm" variant="link">
          <Link href="/archive">{t("archiveSummary.open")}</Link>
        </Button>
      </CardContent>
    </Card>
  );
}
