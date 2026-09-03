"use client";

import {
  CircleAlertIcon,
  LocateFixedIcon,
  PencilLineIcon,
  PlusCircleIcon,
  Settings2Icon,
  Trash2Icon,
} from "lucide-react";
import { useTranslations } from "next-intl";
import { Popover as PopoverPrimitive } from "radix-ui";
import { useLayoutEffect, useRef } from "react";

import { Badge } from "@/components/ui/badge";
import { IconTooltipButton } from "@/components/ui/icon-tooltip-button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  hasManualChange,
  type ReviewFieldDraft,
} from "@/lib/review/editor-state";
import {
  confidenceColorClassName,
  getConfidenceColor,
} from "@/lib/confidence-colors/presentation";
import type { ConfidenceColorBand } from "@/lib/confidence-colors/types";
import type { ReviewSourceSelection } from "@/lib/review/types";
import { getReviewFieldLocatableSources } from "@/lib/review/source-location";
import {
  getDisplayedConfidencePercent,
  getReviewFieldDisplayValues,
  getReviewReasonCodePresentations,
  REVIEW_REASON_BADGE_VARIANTS,
} from "@/lib/review/field-presentation";
import { cn } from "@/lib/utils";

const EMPTY_BOOLEAN = "__empty__";

export interface ReviewFieldRowProps {
  canEdit: boolean;
  confidenceColorBands: readonly ConfidenceColorBand[];
  editing: boolean;
  field: ReviewFieldDraft;
  onChange: (value: string) => void;
  onEdit: () => void;
  onRemove: () => void;
  onSelectSource: (selection: ReviewSourceSelection) => void;
}

export function ReviewFieldRow({
  canEdit,
  confidenceColorBands,
  editing,
  field,
  onChange,
  onEdit,
  onRemove,
  onSelectSource,
}: ReviewFieldRowProps) {
  const t = useTranslations("ReviewWorkspace.fields");
  const manual = hasManualChange(field);
  const hasError =
    field.validations.some((validation) => validation.severity === "error") ||
    ["conflicting", "missing"].includes(field.status);
  const confidencePercent = getDisplayedConfidencePercent(field);
  const displayValues = getReviewFieldDisplayValues(field);
  const sources = getReviewFieldLocatableSources(field);
  const reviewReasonCodePresentations = getReviewReasonCodePresentations(
    field.reviewReasonCodes,
    (code) => t(`reasonCodes.${code}`),
  );

  return (
    <li
      className={cn("space-y-3 px-3 py-3", hasError && "bg-destructive/5")}
      data-review-field-id={field.id || field.clientId}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="font-medium">{field.label}</span>
            {manual ? (
              <Badge className="gap-1" variant="secondary">
                {field.kind === "manual" ? (
                  <PlusCircleIcon aria-hidden="true" className="size-3" />
                ) : (
                  <PencilLineIcon aria-hidden="true" className="size-3" />
                )}
                {field.kind === "manual"
                  ? t("manualAdded")
                  : t("manualChanged")}
              </Badge>
            ) : null}
            {confidencePercent !== null ? (
              <Badge
                aria-label={t("confidenceAria", {
                  score: confidencePercent,
                })}
                className={cn(
                  confidenceColorClassName(
                    getConfidenceColor(confidencePercent, confidenceColorBands),
                  ),
                  manual && "opacity-40 grayscale",
                )}
                title={manual ? t("confidenceOriginal") : undefined}
                variant="outline"
              >
                {t("confidence", { score: confidencePercent })}
              </Badge>
            ) : null}
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-1">
          {!editing && sources.length > 0 ? (
            <IconTooltipButton
              aria-label={t("showSourceAria", { name: field.label })}
              onClick={() =>
                onSelectSource({
                  fieldId: field.id || field.clientId,
                  sources,
                  targetPageNumber: sources[0]!.pageNumber,
                })
              }
              size="icon-sm"
              tooltip={t("showSourceAria", { name: field.label })}
              type="button"
              variant="ghost"
            >
              <LocateFixedIcon />
            </IconTooltipButton>
          ) : null}
          {editing ? (
            <IconTooltipButton
              aria-label={t("deleteAria", { name: field.label })}
              onClick={onRemove}
              size="icon-sm"
              tooltip={t("deleteAria", { name: field.label })}
              type="button"
              variant="ghost"
            >
              <Trash2Icon />
            </IconTooltipButton>
          ) : null}
        </div>
      </div>

      {editing ? (
        <ReviewValueControl field={field} onChange={onChange} />
      ) : canEdit ? (
        <button
          className="block w-full rounded-md border bg-background px-3 py-2 text-left text-sm hover:border-primary/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          onClick={onEdit}
          type="button"
        >
          <ReviewFieldDisplayValues
            values={displayValues}
            fallback={t("notProvided")}
          />
        </button>
      ) : (
        <div className="block w-full rounded-md border bg-background px-3 py-2 text-left text-sm">
          <ReviewFieldDisplayValues
            values={displayValues}
            fallback={t("notProvided")}
          />
        </div>
      )}

      {reviewReasonCodePresentations.length > 0 ? (
        <div
          aria-label={t("reviewReasonsAria")}
          className="flex flex-wrap gap-1.5"
          role="list"
        >
          {reviewReasonCodePresentations.map((presentation, index) => (
            <span key={`${presentation.code}-${index}`} role="listitem">
              <PopoverPrimitive.Root>
                <PopoverPrimitive.Trigger asChild>
                  <Badge
                    asChild
                    className={cn(
                      "h-auto cursor-pointer whitespace-normal px-2 py-0.5 text-left text-[11px] font-normal",
                      presentation.tone === "configuration" &&
                        "border-muted-foreground/30 text-muted-foreground hover:bg-muted/50 hover:text-muted-foreground",
                    )}
                    data-review-reason-tone={presentation.tone}
                    variant={REVIEW_REASON_BADGE_VARIANTS[presentation.tone]}
                  >
                    <button type="button">
                      {presentation.tone === "configuration" ? (
                        <Settings2Icon
                          aria-hidden="true"
                          data-icon="inline-start"
                        />
                      ) : null}
                      {presentation.label}
                    </button>
                  </Badge>
                </PopoverPrimitive.Trigger>
                <PopoverPrimitive.Portal>
                  <PopoverPrimitive.Content
                    align="start"
                    aria-label={t("reasonPopup.detailsAria", {
                      reason: presentation.label,
                    })}
                    className="z-50 w-[min(24rem,calc(100vw-2rem))] space-y-3 rounded-lg border bg-popover p-4 text-sm text-popover-foreground shadow-md outline-none duration-100 data-[side=bottom]:slide-in-from-top-2 data-[side=left]:slide-in-from-right-2 data-[side=right]:slide-in-from-left-2 data-[side=top]:slide-in-from-bottom-2 data-open:animate-in data-open:fade-in-0 data-open:zoom-in-95 data-closed:animate-out data-closed:fade-out-0 data-closed:zoom-out-95"
                    role="dialog"
                    sideOffset={6}
                  >
                    <ReviewReasonPopupSection
                      body={t(
                        `reasonPopup.codes.${presentation.popupKey}.happened`,
                      )}
                      heading={t("reasonPopup.whatHappened")}
                    />
                    <ReviewReasonPopupSection
                      body={t(
                        `reasonPopup.codes.${presentation.popupKey}.meaning`,
                      )}
                      heading={t("reasonPopup.whatItMeans")}
                    />
                    <ReviewReasonPopupSection
                      body={t(
                        `reasonPopup.codes.${presentation.popupKey}.action`,
                      )}
                      heading={t("reasonPopup.whatToDo")}
                    />
                  </PopoverPrimitive.Content>
                </PopoverPrimitive.Portal>
              </PopoverPrimitive.Root>
            </span>
          ))}
        </div>
      ) : null}

      {manual ? (
        <p className="flex items-center gap-1 text-xs text-muted-foreground">
          <PencilLineIcon aria-hidden="true" className="size-3" />
          {confidencePercent === null
            ? t("noManualConfidence")
            : t("confidenceOriginal")}
        </p>
      ) : null}

      {field.validations.map((validation) => (
        <p
          className={cn(
            "flex items-start gap-1.5 text-xs",
            validation.severity === "error"
              ? "font-medium text-destructive"
              : "text-muted-foreground",
          )}
          key={`${validation.code}-${validation.message}`}
          role={validation.severity === "error" ? "alert" : undefined}
        >
          <CircleAlertIcon
            aria-hidden="true"
            className="mt-0.5 size-3 shrink-0"
          />
          {validation.message}
        </p>
      ))}
    </li>
  );
}

function ReviewFieldDisplayValues({
  fallback,
  values,
}: {
  fallback: string;
  values: readonly string[];
}) {
  if (values.length === 0) return fallback;
  return (
    <span className="flex flex-col">
      {values.map((value, index) => (
        <span key={`${value}-${index}`}>{value}</span>
      ))}
    </span>
  );
}

function ReviewReasonPopupSection({
  body,
  heading,
}: {
  body: string;
  heading: string;
}) {
  return (
    <section className="space-y-1">
      <h4 className="font-medium">{heading}</h4>
      <p className="leading-relaxed text-muted-foreground">{body}</p>
    </section>
  );
}

function ReviewValueControl({
  field,
  onChange,
}: {
  field: ReviewFieldDraft;
  onChange: (value: string) => void;
}) {
  const t = useTranslations("ReviewWorkspace.fields");
  const label = t("valueAria", { name: field.label });

  if (field.dataType === "boolean") {
    return (
      <Select
        onValueChange={(value) =>
          onChange(value === EMPTY_BOOLEAN ? "" : value)
        }
        value={field.value ?? EMPTY_BOOLEAN}
      >
        <SelectTrigger aria-label={label} className="w-full">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={EMPTY_BOOLEAN}>{t("notProvided")}</SelectItem>
          <SelectItem value="true">{t("booleanYes")}</SelectItem>
          <SelectItem value="false">{t("booleanNo")}</SelectItem>
        </SelectContent>
      </Select>
    );
  }

  if (field.dataType === "string" || field.dataType === "legacy_scalar") {
    return (
      <AutoResizeTextarea
        label={label}
        onChange={onChange}
        value={field.value ?? ""}
      />
    );
  }

  return (
    <Input
      aria-label={label}
      inputMode={inputMode(field.dataType)}
      onChange={(event) => onChange(event.target.value)}
      type={inputType(field.dataType)}
      value={field.value ?? ""}
    />
  );
}

function AutoResizeTextarea({
  label,
  onChange,
  value,
}: {
  label: string;
  onChange: (value: string) => void;
  value: string;
}) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useLayoutEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    textarea.style.height = "0px";
    textarea.style.height = `${textarea.scrollHeight}px`;
  }, [value]);

  return (
    <Textarea
      aria-label={label}
      className="min-h-8 resize-y overflow-hidden py-1"
      onChange={(event) => onChange(event.target.value)}
      ref={textareaRef}
      rows={1}
      value={value}
    />
  );
}

function inputType(
  dataType: ReviewFieldDraft["dataType"],
): "date" | "datetime-local" | "text" {
  if (dataType === "date") return "date";
  if (dataType === "datetime") return "datetime-local";
  return "text";
}

function inputMode(
  dataType: ReviewFieldDraft["dataType"],
): "decimal" | "numeric" | undefined {
  if (dataType === "number") return "decimal";
  if (dataType === "integer") return "numeric";
  return undefined;
}
