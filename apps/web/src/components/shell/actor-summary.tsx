"use client";

import {
  ChevronDownIcon,
  KeyRoundIcon,
  LanguagesIcon,
  LogOutIcon,
} from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button, buttonVariants } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useAuthActions } from "@/hooks/auth/auth-actions-context";
import { useCurrentActor } from "@/hooks/auth/use-current-actor";
import { Link, usePathname } from "@/i18n/navigation";
import type { Locale } from "@/i18n/routing";
import type { Role } from "@/lib/auth/types";
import { cn } from "@/lib/utils";

import { OwnPasswordSheet } from "./own-password-sheet";

type ShellRoleTranslator = (
  key: "roles.admin" | "roles.operator" | "roles.reviewer" | "roles.viewer",
) => string;

const menuItemClassName = "w-full justify-start";
const languageItemClassName = "h-8 justify-center px-3 text-xs";

interface ActorSummaryProps {
  contentAlign?: "start" | "center" | "end";
  contentSide?: "top" | "right" | "bottom" | "left";
  textClassName?: string;
  triggerClassName?: string;
}

export function ActorSummary({
  contentAlign = "end",
  contentSide = "bottom",
  textClassName,
  triggerClassName,
}: ActorSummaryProps) {
  const t = useTranslations("Shell");
  const activeLocale = useLocale() as Locale;
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const { actor, isLoading } = useCurrentActor();
  const { logout } = useAuthActions();
  const [isLoggingOut, setIsLoggingOut] = useState(false);
  const [isPasswordOpen, setIsPasswordOpen] = useState(false);
  const displayName = actor?.email ?? t("actorFallback");
  const roleText =
    actor && actor.roles.length > 0
      ? actor.roles.map((role) => roleLabel(role, t)).join(", ")
      : t("roles.viewer");
  const canChangePassword = actor?.auth_providers.includes("local") ?? false;
  const queryString = searchParams.toString();
  const currentHref = queryString ? `${pathname}?${queryString}` : pathname;

  async function handleLogout() {
    setIsLoggingOut(true);

    try {
      await logout();
    } finally {
      router.replace(`/${activeLocale}/login`);
      setIsLoggingOut(false);
    }
  }

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            aria-label={t("accountMenu.open")}
            className={cn("h-11 gap-3 px-2", triggerClassName)}
            type="button"
            variant="ghost"
          >
            <Avatar className="size-9">
              <AvatarFallback className="bg-primary/10 text-primary">
                {actor?.email ? initials(actor.email) : "DM"}
              </AvatarFallback>
            </Avatar>
            <span
              className={cn(
                "hidden min-w-0 text-left leading-tight md:block",
                textClassName,
              )}
            >
              <span className="block max-w-44 truncate text-sm font-semibold">
                {isLoading ? t("actorLoading") : displayName}
              </span>
              <span className="block max-w-44 truncate text-xs text-muted-foreground">
                {roleText}
              </span>
            </span>
            <ChevronDownIcon
              aria-hidden="true"
              className="hidden size-4 text-muted-foreground md:block"
            />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent
          align={contentAlign}
          className="w-72"
          side={contentSide}
          sideOffset={8}
        >
          <DropdownMenuGroup>
            <DropdownMenuLabel>
              <p className="truncate text-sm font-semibold">{displayName}</p>
              <p className="truncate text-xs text-muted-foreground">
                {roleText}
              </p>
            </DropdownMenuLabel>
          </DropdownMenuGroup>
          <DropdownMenuSeparator />
          <DropdownMenuGroup>
            <DropdownMenuLabel className="flex items-center gap-2">
              <span className="flex size-4 items-center justify-center">
                <LanguagesIcon className="size-3" />
              </span>
              {t("languageSwitcher.label")}
            </DropdownMenuLabel>
            <div className="grid grid-cols-2 gap-1 px-1.5 py-1">
              {(["pl", "en"] as const).map((locale) => {
                const isActive = locale === activeLocale;
                const labelState = isActive ? "selected" : "switchTo";

                return (
                  <DropdownMenuItem
                    asChild
                    className={buttonVariants({
                      className: languageItemClassName,
                      size: "sm",
                      variant: isActive ? "primary" : "outline",
                    })}
                    key={locale}
                  >
                    <Link
                      aria-current={isActive ? "true" : undefined}
                      aria-label={t(
                        `languageSwitcher.options.${locale}.${labelState}`,
                      )}
                      href={currentHref}
                      locale={locale}
                    >
                      {locale.toUpperCase()}
                    </Link>
                  </DropdownMenuItem>
                );
              })}
            </div>
          </DropdownMenuGroup>
          <DropdownMenuSeparator />
          <DropdownMenuGroup>
            {canChangePassword ? (
              <DropdownMenuItem asChild>
                <button
                  className={menuItemClassName}
                  onClick={() => setIsPasswordOpen(true)}
                  type="button"
                >
                  <KeyRoundIcon data-icon="inline-start" />
                  {t("accountMenu.changePassword")}
                </button>
              </DropdownMenuItem>
            ) : null}
            <DropdownMenuItem asChild>
              <button
                className={menuItemClassName}
                disabled={isLoggingOut}
                onClick={() => void handleLogout()}
                type="button"
              >
                <LogOutIcon data-icon="inline-start" />
                {isLoggingOut
                  ? t("accountMenu.loggingOut")
                  : t("accountMenu.logout")}
              </button>
            </DropdownMenuItem>
          </DropdownMenuGroup>
        </DropdownMenuContent>
      </DropdownMenu>

      <OwnPasswordSheet
        onOpenChange={setIsPasswordOpen}
        open={isPasswordOpen}
      />
    </>
  );
}

function initials(email: string): string {
  const [name] = email.split("@");
  const parts = name.split(/[._-]+/).filter(Boolean);
  const first = parts[0]?.[0] ?? email[0] ?? "D";
  const second = parts[1]?.[0] ?? parts[0]?.[1] ?? "M";
  return `${first}${second}`.toUpperCase();
}

function roleLabel(role: Role, t: ShellRoleTranslator) {
  switch (role) {
    case "admin":
      return t("roles.admin");
    case "operator":
      return t("roles.operator");
    case "reviewer":
      return t("roles.reviewer");
    case "viewer":
      return t("roles.viewer");
    default:
      return role;
  }
}
