"use client";

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import type { ConnectorConfigurationTestResult } from "@/lib/connector-configurations/api";
import type { ConnectorConfigurationTestDialogMessages } from "@/lib/connector-configurations/extensions";
import { cn } from "@/lib/utils";

interface ConnectionTestDialogProps {
  messages: ConnectorConfigurationTestDialogMessages;
  onClose: () => void;
  open: boolean;
  result: ConnectorConfigurationTestResult;
  summary: string;
}

export function ConnectionTestDialog({
  messages,
  onClose,
  open,
  result,
  summary,
}: ConnectionTestDialogProps) {
  return (
    <AlertDialog
      onOpenChange={(nextOpen) => {
        if (!nextOpen) onClose();
      }}
      open={open}
    >
      <AlertDialogContent
        className="max-h-[min(52rem,calc(100vh-2rem))] grid-rows-[auto_minmax(0,1fr)_auto]"
        size="lg"
      >
        <AlertDialogHeader className="border-b">
          <div className="flex w-full items-start justify-between gap-4">
            <div className="space-y-1.5">
              <AlertDialogTitle>{messages.title}</AlertDialogTitle>
              <AlertDialogDescription>{summary}</AlertDialogDescription>
            </div>
            <span
              className={cn(
                "shrink-0 rounded-full px-2.5 py-1 text-xs font-semibold",
                result.status === "success"
                  ? "bg-emerald-100 text-emerald-800"
                  : "bg-destructive/10 text-destructive",
              )}
            >
              {result.status === "success"
                ? messages.outcomeLabels.success
                : messages.outcomeLabels.error}
            </span>
          </div>
        </AlertDialogHeader>

        <div className="min-h-0 space-y-3 overflow-y-auto px-5 py-4">
          {result.diagnostics.map((diagnostic, index) => (
            <section
              className="overflow-hidden rounded-lg border bg-background"
              key={`${diagnostic.code}-${index}`}
            >
              <div className="flex items-center justify-between gap-3 border-b bg-muted/40 px-4 py-3">
                <h3 className="font-medium">
                  {index + 1}.{" "}
                  {messages.stepLabels[diagnostic.code] ?? diagnostic.code}
                </h3>
                <span
                  className={cn(
                    "rounded-full px-2 py-0.5 text-xs font-medium",
                    diagnostic.status === "success" &&
                      "bg-emerald-100 text-emerald-800",
                    diagnostic.status === "error" &&
                      "bg-destructive/10 text-destructive",
                    diagnostic.status === "info" && "bg-blue-100 text-blue-800",
                  )}
                >
                  {messages.outcomeLabels[diagnostic.status]}
                </span>
              </div>
              <dl className="divide-y">
                {Object.entries(diagnostic.details).map(([key, value]) => (
                  <div
                    className="grid gap-1 px-4 py-2.5 sm:grid-cols-[14rem_minmax(0,1fr)] sm:gap-4"
                    key={key}
                  >
                    <dt className="text-sm text-muted-foreground">
                      {messages.detailLabels[key] ?? key}
                    </dt>
                    <dd className="whitespace-pre-wrap break-words font-mono text-sm">
                      {value}
                    </dd>
                  </div>
                ))}
              </dl>
            </section>
          ))}
        </div>

        <AlertDialogFooter>
          <AlertDialogAction onClick={onClose}>
            {messages.closeLabel}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
