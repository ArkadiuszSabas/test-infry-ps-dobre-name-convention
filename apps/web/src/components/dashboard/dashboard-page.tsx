"use client";

import { useQuery } from "@tanstack/react-query";
import { LayoutDashboardIcon, RefreshCwIcon } from "lucide-react";
import { useFormatter, useTranslations } from "next-intl";
import { useState } from "react";

import { DashboardHero } from "@/components/dashboard/dashboard-hero";
import { DashboardLists } from "@/components/dashboard/dashboard-lists";
import {
  DashboardOverviewGrid,
  DashboardOverviewSkeleton,
  OperationalStatusCard,
} from "@/components/dashboard/dashboard-overview";
import { GreetingHeading } from "@/components/dashboard/greeting-heading";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { PageHeader } from "@/components/ui/page-header";
import { PageShell } from "@/components/ui/page-shell";
import { dashboardClient } from "@/lib/dashboard/api";
import type { DashboardWindowDays } from "@/lib/dashboard/types";

export function DashboardPage() {
  const t = useTranslations("Dashboard");
  const format = useFormatter();
  const [windowDays, setWindowDays] = useState<DashboardWindowDays>(7);
  const overviewQuery = useQuery({
    queryKey: ["dashboard", "overview", windowDays],
    queryFn: ({ signal }) =>
      dashboardClient.getOverview(windowDays, { signal }),
    retry: false,
  });
  const overview = overviewQuery.data;

  return (
    <PageShell className="max-w-[1500px]">
      <PageHeader
        actions={
          overview ? (
            <p className="text-xs text-muted-foreground">
              {t("generatedAt", {
                value: format.dateTime(new Date(overview.generatedAt), {
                  dateStyle: "medium",
                  timeStyle: "short",
                }),
              })}
            </p>
          ) : undefined
        }
        description={t("subtitle")}
        icon={LayoutDashboardIcon}
        title={<GreetingHeading />}
      />

      <div className="grid gap-5 lg:grid-cols-[minmax(0,2fr)_minmax(18rem,1fr)]">
        <DashboardHero />
        {overview ? (
          <OperationalStatusCard status={overview.operationalStatus} />
        ) : (
          <DashboardOverviewSkeleton compact />
        )}
      </div>

      {overviewQuery.isError ? (
        <Card role="alert" className="border-destructive/30 bg-destructive/5">
          <CardContent className="flex flex-col items-start gap-3 py-5 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="font-medium">{t("error.title")}</p>
              <p className="text-sm text-muted-foreground">
                {t("error.description")}
              </p>
            </div>
            <Button
              onClick={() => overviewQuery.refetch()}
              type="button"
              variant="outline"
            >
              <RefreshCwIcon data-icon="inline-start" />
              {t("error.retry")}
            </Button>
          </CardContent>
        </Card>
      ) : null}

      {overview ? (
        <>
          <DashboardOverviewGrid
            onWindowChange={setWindowDays}
            overview={overview}
            selectedWindow={windowDays}
          />
          <DashboardLists
            requiresAttention={overview.requiresAttention}
            toReview={overview.toReview}
          />
        </>
      ) : overviewQuery.isError ? null : (
        <DashboardOverviewSkeleton />
      )}
    </PageShell>
  );
}
