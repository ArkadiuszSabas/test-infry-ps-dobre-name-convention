"use client";

import { useTranslations } from "next-intl";
import { useSyncExternalStore } from "react";

import { useCurrentActor } from "@/hooks/auth/use-current-actor";
import { getGreetingName, getGreetingPeriod } from "@/lib/dashboard/greeting";

const emptySubscribe = () => () => {};

function useCurrentHour(): number | null {
  return useSyncExternalStore(
    emptySubscribe,
    () => new Date().getHours(),
    () => null,
  );
}

export function GreetingHeading() {
  const t = useTranslations("Dashboard");
  const { actor } = useCurrentActor();
  const hour = useCurrentHour();

  if (hour === null) {
    return <span>{t("title")}</span>;
  }

  const period = getGreetingPeriod(hour);
  const name = getGreetingName(actor?.email ?? null);
  const greeting = name
    ? t(`welcome.greeting.${period}`, { name })
    : t(`welcome.greetingNeutral.${period}`);

  return <span data-testid="dashboard-greeting">{greeting}</span>;
}
