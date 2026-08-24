"use client";

import { ShieldAlertIcon } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuthActions } from "@/hooks/auth/auth-actions-context";
import { useCurrentActor } from "@/hooks/auth/use-current-actor";
import { Link } from "@/i18n/navigation";
import { isAuthenticationError } from "@/lib/auth/errors";
import { canAccessRoute, type AppRouteId } from "@/lib/navigation/route-policy";

interface AuthGuardProps {
  children: ReactNode;
  routeId?: AppRouteId;
}

export function AuthGuard({ children, routeId }: AuthGuardProps) {
  const t = useTranslations("AuthGuard");
  const locale = useLocale();
  const router = useRouter();
  const { clearAuthState, csrfToken, refreshCsrf } = useAuthActions();
  const { actor, error, isAuthenticated, isError, isLoading, refetch } =
    useCurrentActor();

  useEffect(() => {
    if (!isError || !isAuthenticationError(error)) {
      return;
    }

    clearAuthState();
    const currentPath =
      window.location.pathname + window.location.search + window.location.hash;
    router.replace(
      `/${locale}/login?redirect_to=${encodeURIComponent(currentPath)}`,
    );
  }, [clearAuthState, error, isError, locale, router]);

  useEffect(() => {
    if (!actor || csrfToken) {
      return;
    }

    void refreshCsrf().catch((csrfError: unknown) => {
      if (isAuthenticationError(csrfError)) {
        clearAuthState();
        router.replace(`/${locale}/login`);
      }
    });
  }, [actor, clearAuthState, csrfToken, locale, refreshCsrf, router]);

  if (isLoading || (isError && isAuthenticationError(error))) {
    return (
      <div className="flex h-dvh items-center justify-center overflow-y-auto bg-background p-6">
        <div className="flex w-full max-w-sm flex-col gap-4">
          <Skeleton className="h-10 w-48" />
          <Skeleton className="h-32 w-full" />
          <p className="text-sm text-muted-foreground">{t("loading")}</p>
        </div>
      </div>
    );
  }

  if (isError || !isAuthenticated) {
    return (
      <div className="flex h-dvh items-center justify-center overflow-y-auto bg-background p-6">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle
              aria-level={1}
              className="flex items-center gap-2"
              role="heading"
            >
              <ShieldAlertIcon data-icon="inline-start" />
              {t("errorTitle")}
            </CardTitle>
            <CardDescription>{t("errorDescription")}</CardDescription>
          </CardHeader>
          <CardContent>
            <Button onClick={() => void refetch()}>{t("retry")}</Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (routeId && !canAccessRoute(actor, routeId)) {
    return (
      <div className="flex h-dvh items-center justify-center overflow-y-auto bg-background p-6">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle
              aria-level={1}
              className="flex items-center gap-2"
              role="heading"
            >
              <ShieldAlertIcon data-icon="inline-start" />
              {t("unauthorizedTitle")}
            </CardTitle>
            <CardDescription>{t("unauthorizedDescription")}</CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild>
              <Link href="/">{t("returnToDashboard")}</Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return children;
}
