import { FileTextIcon, UploadIcon } from "lucide-react";
import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Link } from "@/i18n/navigation";

export function DashboardHero() {
  const t = useTranslations("Dashboard");

  return (
    <Card className="relative min-h-64 overflow-hidden border-primary/15 bg-gradient-to-br from-primary/5 via-background to-accent/70">
      <CardContent className="relative z-10 flex h-full flex-col items-start justify-center gap-4 p-7 sm:max-w-[62%] sm:p-9">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">
            {t("welcome.heading")}
          </h2>
          <p className="mt-3 text-sm leading-6 text-muted-foreground">
            {t("welcome.description")}
          </p>
        </div>
        <Button asChild size="lg">
          <Link href="/documents?upload=true">
            <UploadIcon data-icon="inline-start" />
            {t("welcome.cta")}
          </Link>
        </Button>
      </CardContent>
      <div
        aria-hidden="true"
        className="absolute right-4 bottom-[-2rem] hidden rotate-[-8deg] sm:block"
      >
        <div className="rounded-xl border border-primary/20 bg-background/90 p-8 shadow-xl">
          <FileTextIcon
            className="size-28 text-primary/25"
            strokeWidth={1.25}
          />
        </div>
      </div>
    </Card>
  );
}
