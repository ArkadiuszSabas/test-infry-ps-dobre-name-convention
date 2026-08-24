"use client";

import {
  ArrowRightIcon,
  CableIcon,
  GitBranchIcon,
  UserCheckIcon,
  Settings2Icon,
  ShieldCheckIcon,
  UsersRoundIcon,
} from "lucide-react";
import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { IconFrame } from "@/components/ui/icon-frame";
import { PageHeader } from "@/components/ui/page-header";
import { PageShell } from "@/components/ui/page-shell";
import { useCurrentActor } from "@/hooks/auth/use-current-actor";
import { Link } from "@/i18n/navigation";
import {
  getAccessibleAdminEntryRoutes,
  type AdminEntryRouteId,
} from "@/lib/navigation/route-policy";

const adminEntryIcons: Record<AdminEntryRouteId, typeof UsersRoundIcon> = {
  adminApprovals: UserCheckIcon,
  adminDictionaries: Settings2Icon,
  adminConnectors: CableIcon,
  adminPipelines: GitBranchIcon,
  adminUsers: UsersRoundIcon,
};

export function AdminPage() {
  const t = useTranslations("Admin");
  const { actor } = useCurrentActor();
  const entries = getAccessibleAdminEntryRoutes(actor);

  return (
    <PageShell>
      <PageHeader
        description={t("description")}
        descriptionClassName="max-w-2xl"
        icon={ShieldCheckIcon}
        title={t("title")}
      />

      <section className="grid gap-5 md:grid-cols-2">
        {entries.map((entry) => {
          const Icon = adminEntryIcons[entry.id];

          return (
            <Card
              key={entry.id}
              className="min-h-44 transition-colors hover:bg-accent hover:text-accent-foreground"
            >
              <CardHeader className="grid-cols-[minmax(0,1fr)_auto] px-5">
                <CardTitle className="text-base font-semibold">
                  {t(`entries.${entry.id}.title`)}
                </CardTitle>
                <CardAction>
                  <IconFrame icon={Icon} />
                </CardAction>
                <CardDescription>
                  {t(`entries.${entry.id}.description`)}
                </CardDescription>
              </CardHeader>
              <CardContent className="mt-auto px-5">
                <Button asChild variant="secondary">
                  <Link href={entry.href}>
                    {t("open")}
                    <ArrowRightIcon data-icon="inline-end" />
                  </Link>
                </Button>
              </CardContent>
            </Card>
          );
        })}
      </section>
    </PageShell>
  );
}
