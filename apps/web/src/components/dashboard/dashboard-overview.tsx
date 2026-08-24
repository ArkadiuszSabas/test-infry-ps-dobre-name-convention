"use client";

import { AlertTriangleIcon, Clock3Icon, RefreshCwIcon } from "lucide-react";
import { useFormatter, useTranslations } from "next-intl";
import { CartesianGrid, Line, LineChart, XAxis, YAxis } from "recharts";

import {
  ArchiveSummaryCard,
  OcrTimingCard,
} from "@/components/dashboard/dashboard-metrics";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  ChartContainer,
  ChartLegend,
  ChartLegendContent,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart";
import { Skeleton } from "@/components/ui/skeleton";
import type {
  DashboardOverview,
  DashboardWindowDays,
} from "@/lib/dashboard/types";

interface DashboardOverviewGridProps {
  overview: DashboardOverview;
  selectedWindow: DashboardWindowDays;
  onWindowChange: (windowDays: DashboardWindowDays) => void;
}

export function DashboardOverviewGrid({
  overview,
  selectedWindow,
  onWindowChange,
}: DashboardOverviewGridProps) {
  return (
    <div className="grid gap-5 lg:grid-cols-[minmax(0,2fr)_minmax(18rem,1fr)]">
      <ActivityCard
        activity={overview.activity}
        onWindowChange={onWindowChange}
        selectedWindow={selectedWindow}
      />
      <div className="grid gap-5">
        <OcrTimingCard
          timing={overview.ocrTiming}
          windowDays={overview.windowDays}
        />
        <ArchiveSummaryCard
          addedInWindow={overview.archive.addedInWindow}
          total={overview.archive.total}
          windowDays={overview.windowDays}
        />
      </div>
    </div>
  );
}

export function OperationalStatusCard({
  status,
}: {
  status: DashboardOverview["operationalStatus"];
}) {
  const t = useTranslations("Dashboard");
  const format = useFormatter();
  const rows = [
    {
      icon: Clock3Icon,
      label: t("operational.toReview"),
      tone: "text-amber-600 bg-amber-500/10",
      value: status.toReview,
    },
    {
      icon: RefreshCwIcon,
      label: t("operational.processing"),
      tone: "text-blue-600 bg-blue-500/10",
      value: status.processing,
    },
    {
      icon: AlertTriangleIcon,
      label: t("operational.requiresAttention"),
      tone: "text-orange-600 bg-orange-500/10",
      value: status.requiresAttention,
    },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("operational.title")}</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-1">
        {rows.map(({ icon: Icon, label, tone, value }) => (
          <div
            className="grid grid-cols-[2.5rem_3.5rem_1fr] items-center gap-3 border-b py-3 last:border-0"
            key={label}
          >
            <span
              className={`flex size-10 items-center justify-center rounded-full ${tone}`}
            >
              <Icon aria-hidden="true" className="size-5" />
            </span>
            <span className="text-2xl font-semibold tabular-nums">
              {format.number(value)}
            </span>
            <span className="text-sm text-muted-foreground">{label}</span>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

function ActivityCard({
  activity,
  selectedWindow,
  onWindowChange,
}: {
  activity: DashboardOverview["activity"];
  selectedWindow: DashboardWindowDays;
  onWindowChange: (windowDays: DashboardWindowDays) => void;
}) {
  const t = useTranslations("Dashboard");
  const format = useFormatter();
  const chartConfig = {
    accepted: {
      color: "var(--chart-4)",
      label: t("activity.accepted"),
    },
    successfulOcr: {
      color: "var(--chart-1)",
      label: t("activity.successfulOcr"),
    },
    archived: {
      color: "var(--chart-2)",
      label: t("activity.archived"),
    },
  } satisfies ChartConfig;

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between gap-4">
        <CardTitle>{t("activity.title")}</CardTitle>
        <div
          aria-label={t("window.aria")}
          className="flex rounded-lg bg-muted p-1"
          role="group"
        >
          {([7, 30] as const).map((windowDays) => (
            <Button
              aria-pressed={selectedWindow === windowDays}
              className="h-8 px-3"
              key={windowDays}
              onClick={() => onWindowChange(windowDays)}
              type="button"
              variant={selectedWindow === windowDays ? "outline" : "ghost"}
            >
              {t("window.days", { count: windowDays })}
            </Button>
          ))}
        </div>
      </CardHeader>
      <CardContent>
        <ChartContainer
          aria-label={t("activity.aria")}
          className="h-64 w-full aspect-auto"
          config={chartConfig}
        >
          <LineChart accessibilityLayer data={activity}>
            <CartesianGrid vertical={false} />
            <XAxis
              axisLine={false}
              dataKey="date"
              tickFormatter={(value: string) =>
                format.dateTime(new Date(`${value}T00:00:00Z`), {
                  day: "2-digit",
                  month: "short",
                })
              }
              tickLine={false}
              tickMargin={10}
            />
            <YAxis allowDecimals={false} axisLine={false} tickLine={false} />
            <ChartTooltip content={<ChartTooltipContent />} />
            <ChartLegend content={<ChartLegendContent />} />
            <Line
              dataKey="accepted"
              dot={false}
              stroke="var(--color-accepted)"
              strokeWidth={2}
              type="monotone"
            />
            <Line
              dataKey="successfulOcr"
              dot={false}
              stroke="var(--color-successfulOcr)"
              strokeWidth={2}
              type="monotone"
            />
            <Line
              dataKey="archived"
              dot={false}
              stroke="var(--color-archived)"
              strokeWidth={2}
              type="monotone"
            />
          </LineChart>
        </ChartContainer>
        <table className="sr-only">
          <caption>{t("activity.aria")}</caption>
          <thead>
            <tr>
              <th>{t("activity.date")}</th>
              <th>{t("activity.accepted")}</th>
              <th>{t("activity.successfulOcr")}</th>
              <th>{t("activity.archived")}</th>
            </tr>
          </thead>
          <tbody>
            {activity.map((day) => (
              <tr key={day.date}>
                <td>{day.date}</td>
                <td>{day.accepted}</td>
                <td>{day.successfulOcr}</td>
                <td>{day.archived}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </CardContent>
    </Card>
  );
}

export function DashboardOverviewSkeleton({
  compact = false,
}: {
  compact?: boolean;
}) {
  if (compact) {
    return (
      <Card aria-busy="true" data-testid="dashboard-overview-loading">
        <CardContent className="grid gap-4 py-6">
          <Skeleton className="h-6 w-40" />
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-12 w-full" />
        </CardContent>
      </Card>
    );
  }

  return (
    <div
      aria-busy="true"
      className="grid gap-5 lg:grid-cols-[minmax(0,2fr)_minmax(18rem,1fr)]"
      data-testid="dashboard-overview-loading"
    >
      <Skeleton className="h-80 w-full rounded-xl" />
      <div className="grid gap-5">
        <Skeleton className="h-48 w-full rounded-xl" />
        <Skeleton className="h-28 w-full rounded-xl" />
      </div>
    </div>
  );
}
