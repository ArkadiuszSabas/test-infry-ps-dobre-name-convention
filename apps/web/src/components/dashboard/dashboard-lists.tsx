import {
  AlertTriangleIcon,
  ChevronRightIcon,
  FileTextIcon,
} from "lucide-react";
import { useFormatter, useTranslations } from "next-intl";
import type { ReactNode } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Link } from "@/i18n/navigation";
import type { DashboardDocumentItem } from "@/lib/dashboard/types";

interface DashboardListsProps {
  toReview: DashboardDocumentItem[];
  requiresAttention: DashboardDocumentItem[];
}

export function DashboardLists({
  toReview,
  requiresAttention,
}: DashboardListsProps) {
  const t = useTranslations("Dashboard");

  return (
    <div className="grid gap-5 lg:grid-cols-2">
      <DocumentListCard
        action={
          <Button asChild size="sm" variant="link">
            <Link href="/documents">{t("lists.viewInbox")}</Link>
          </Button>
        }
        empty={t("lists.toReviewEmpty")}
        items={toReview}
        title={t("lists.toReview")}
      />
      <DocumentListCard
        empty={t("lists.attentionEmpty")}
        items={requiresAttention}
        title={t("lists.requiresAttention")}
        tone="attention"
      />
    </div>
  );
}

function DocumentListCard({
  action,
  empty,
  items,
  title,
  tone = "review",
}: {
  action?: ReactNode;
  empty: string;
  items: DashboardDocumentItem[];
  title: string;
  tone?: "attention" | "review";
}) {
  const t = useTranslations("Dashboard");
  const format = useFormatter();

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between gap-4">
        <CardTitle>{title}</CardTitle>
        {action}
      </CardHeader>
      <CardContent>
        {items.length === 0 ? (
          <p className="py-6 text-sm text-muted-foreground">{empty}</p>
        ) : (
          <ul className="divide-y">
            {items.map((item) => (
              <li key={item.documentId}>
                <Link
                  className="grid grid-cols-[2rem_minmax(0,1fr)_auto] items-center gap-3 py-3 transition-colors hover:text-primary"
                  href={`/documents/${item.documentId}`}
                >
                  {tone === "attention" ? (
                    <AlertTriangleIcon
                      aria-hidden="true"
                      className="size-5 text-orange-600"
                    />
                  ) : (
                    <FileTextIcon
                      aria-hidden="true"
                      className="size-5 text-primary"
                    />
                  )}
                  <span className="min-w-0">
                    <span className="block truncate text-sm font-medium">
                      {item.filename}
                    </span>
                    <span className="mt-1 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                      {item.documentType ? (
                        <span>{item.documentType}</span>
                      ) : null}
                      <span>
                        {format.dateTime(new Date(item.eventAt), {
                          dateStyle: "medium",
                          timeStyle: "short",
                        })}
                      </span>
                    </span>
                  </span>
                  <span className="flex items-center gap-2">
                    <Badge
                      variant={
                        tone === "attention" ? "destructive" : "secondary"
                      }
                    >
                      {item.problemType ?? t(statusMessageKey(item.status))}
                    </Badge>
                    <ChevronRightIcon aria-hidden="true" className="size-4" />
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}

function statusMessageKey(
  status: string,
):
  | "statuses.received"
  | "statuses.waiting_for_review"
  | "statuses.in_review"
  | "statuses.approved"
  | "statuses.pending"
  | "statuses.running"
  | "statuses.succeeded"
  | "statuses.partial_failed"
  | "statuses.failed" {
  switch (status) {
    case "waiting_for_review":
      return "statuses.waiting_for_review";
    case "in_review":
      return "statuses.in_review";
    case "approved":
      return "statuses.approved";
    case "pending":
      return "statuses.pending";
    case "running":
      return "statuses.running";
    case "succeeded":
      return "statuses.succeeded";
    case "partial_failed":
      return "statuses.partial_failed";
    case "failed":
      return "statuses.failed";
    default:
      return "statuses.received";
  }
}
