"use client";

import { PlusIcon, Trash2Icon } from "lucide-react";
import { useTranslations } from "next-intl";
import { useMemo, useState, type FormEvent } from "react";

import {
  CatalogFormActions,
  CatalogFormSheet,
  CatalogFormSheetContent,
} from "@/components/admin/catalog/catalog-form-sheet";
import { Button } from "@/components/ui/button";
import { Field, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { confidenceColorClassName } from "@/lib/confidence-colors/presentation";
import {
  CONFIDENCE_COLOR_PALETTE,
  type ConfidenceColor,
  type ConfidenceColorBand,
  type ConfidenceColorSettings,
} from "@/lib/confidence-colors/types";
import {
  validateConfidenceColorBands,
  type ConfidenceColorValidationIssue,
  type EditableConfidenceColorBand,
} from "@/lib/confidence-colors/validation";
import { cn } from "@/lib/utils";

export interface ConfidenceColorSettingsSheetProps {
  error: string | null;
  isPending: boolean;
  onCancel: () => void;
  onSubmit: (bands: ConfidenceColorBand[]) => void;
  saveDisabled?: boolean;
  settings: ConfidenceColorSettings;
}

export function ConfidenceColorSettingsSheet({
  error,
  isPending,
  onCancel,
  onSubmit,
  saveDisabled = false,
  settings,
}: ConfidenceColorSettingsSheetProps) {
  const t = useTranslations("AdminOcrPipelines.confidenceColors");
  const [bands, setBands] = useState<EditableConfidenceColorBand[]>(() =>
    settings.bands.map((band) => ({ ...band })),
  );
  const [submitted, setSubmitted] = useState(false);
  const validation = useMemo(
    () => validateConfidenceColorBands(bands),
    [bands],
  );
  const visibleIssues = submitted ? validation.issues : [];
  const footerError =
    visibleIssues.length > 0 ? t(`errors.${visibleIssues[0]?.code}`) : error;

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitted(true);
    if (!validation.valid || !validation.bands) {
      return;
    }
    onSubmit(validation.bands);
  }

  function updateBoundary(
    index: number,
    field: "end" | "start",
    value: string,
  ) {
    setBands((current) =>
      current.map((band, bandIndex) =>
        bandIndex === index
          ? {
              ...band,
              [field]: value === "" ? null : Number(value),
            }
          : band,
      ),
    );
    setSubmitted(false);
  }

  function updateColor(index: number, color: ConfidenceColor) {
    setBands((current) =>
      current.map((band, bandIndex) =>
        bandIndex === index ? { ...band, color } : band,
      ),
    );
    setSubmitted(false);
  }

  function addBand() {
    setBands((current) => splitWidestBand(current));
    setSubmitted(false);
  }

  function removeBand(index: number) {
    setBands((current) => mergeRemovedBand(current, index));
    setSubmitted(false);
  }

  return (
    <CatalogFormSheetContent
      onEscapeKeyDown={(event) => {
        if (isPending) event.preventDefault();
      }}
      onInteractOutside={(event) => {
        if (isPending) event.preventDefault();
      }}
      showCloseButton={!isPending}
      size="wide"
    >
      <CatalogFormSheet
        description={t("description")}
        footer={
          <CatalogFormActions
            cancelLabel={t("cancel")}
            error={footerError}
            isPending={isPending}
            onCancel={onCancel}
            saveDisabled={saveDisabled}
            saveLabel={t("save")}
            savingLabel={t("saving")}
          />
        }
        onSubmit={handleSubmit}
        title={t("title")}
      >
        <div className="rounded-md border bg-muted/20 p-3 text-sm text-muted-foreground">
          {t("coverageHint")}
        </div>

        <div className="space-y-3">
          {bands.map((band, index) => {
            const bandIssues = visibleIssues.filter(
              (issue) => issue.bandIndex === index,
            );

            return (
              <div
                className="grid gap-3 rounded-md border p-3 sm:grid-cols-[1fr_1fr_minmax(10rem,1.2fr)_auto]"
                key={index}
              >
                <BoundaryField
                  error={fieldHasIssue(bandIssues, "start")}
                  disabled={isPending || saveDisabled}
                  id={`confidence-band-${index}-start`}
                  label={t("fields.start")}
                  onChange={(value) => updateBoundary(index, "start", value)}
                  value={band.start}
                />
                <BoundaryField
                  error={fieldHasIssue(bandIssues, "end")}
                  disabled={isPending || saveDisabled}
                  id={`confidence-band-${index}-end`}
                  label={t("fields.end")}
                  onChange={(value) => updateBoundary(index, "end", value)}
                  value={band.end}
                />
                <Field>
                  <FieldLabel htmlFor={`confidence-band-${index}-color`}>
                    {t("fields.color")}
                  </FieldLabel>
                  <Select
                    disabled={isPending || saveDisabled}
                    onValueChange={(value) =>
                      updateColor(index, value as ConfidenceColor)
                    }
                    value={band.color}
                  >
                    <SelectTrigger
                      aria-label={t("fields.colorAria", {
                        number: index + 1,
                      })}
                      id={`confidence-band-${index}-color`}
                    >
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {CONFIDENCE_COLOR_PALETTE.map((color) => (
                        <SelectItem key={color} value={color}>
                          <span className="flex items-center gap-2">
                            <span
                              aria-hidden="true"
                              className={cn(
                                "size-3 rounded-full border",
                                confidenceColorClassName(color),
                              )}
                            />
                            {t(`colors.${color}`)}
                          </span>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </Field>
                <Button
                  aria-label={t("removeAria", { number: index + 1 })}
                  className="self-end"
                  disabled={isPending || saveDisabled || bands.length === 1}
                  onClick={() => removeBand(index)}
                  size="icon"
                  type="button"
                  variant="ghost"
                >
                  <Trash2Icon />
                </Button>
                {bandIssues.length > 0 ? (
                  <p
                    className="text-xs font-medium text-destructive sm:col-span-4"
                    role="alert"
                  >
                    {t(`errors.${bandIssues[0]?.code}`)}
                  </p>
                ) : null}
              </div>
            );
          })}
        </div>

        <Button
          className="self-start"
          disabled={isPending || saveDisabled || bands.length >= 5}
          onClick={addBand}
          type="button"
          variant="outline"
        >
          <PlusIcon data-icon="inline-start" />
          {t("add")}
        </Button>
      </CatalogFormSheet>
    </CatalogFormSheetContent>
  );
}

function BoundaryField({
  disabled,
  error,
  id,
  label,
  onChange,
  value,
}: {
  disabled: boolean;
  error: boolean;
  id: string;
  label: string;
  onChange: (value: string) => void;
  value: number | null;
}) {
  return (
    <Field>
      <FieldLabel htmlFor={id}>{label}</FieldLabel>
      <Input
        aria-invalid={error}
        disabled={disabled}
        id={id}
        inputMode="numeric"
        max={100}
        min={0}
        onChange={(event) => onChange(event.target.value)}
        step={1}
        type="number"
        value={value ?? ""}
      />
    </Field>
  );
}

function fieldHasIssue(
  issues: readonly ConfidenceColorValidationIssue[],
  field: "end" | "start",
): boolean {
  return issues.some(
    (issue) =>
      issue.field === field ||
      issue.code === "invertedRange" ||
      issue.code === "gapOrOverlap",
  );
}

function splitWidestBand(
  bands: readonly EditableConfidenceColorBand[],
): EditableConfidenceColorBand[] {
  if (bands.length >= 5) {
    return [...bands];
  }
  const splittable = bands
    .map((band, index) => ({
      index,
      width:
        band.start === null || band.end === null ? -1 : band.end - band.start,
    }))
    .sort((left, right) => right.width - left.width)[0];
  if (!splittable || splittable.width < 1) {
    return [...bands];
  }

  const source = bands[splittable.index];
  if (!source || source.start === null || source.end === null) {
    return [...bands];
  }
  const splitAt = Math.floor((source.start + source.end) / 2);
  const color =
    CONFIDENCE_COLOR_PALETTE[
      (CONFIDENCE_COLOR_PALETTE.indexOf(source.color) + 1) %
        CONFIDENCE_COLOR_PALETTE.length
    ] ?? "blue";

  return bands.flatMap((band, index) =>
    index === splittable.index
      ? [
          { ...band, end: splitAt },
          { color, end: source.end, start: splitAt + 1 },
        ]
      : [{ ...band }],
  );
}

function mergeRemovedBand(
  bands: readonly EditableConfidenceColorBand[],
  index: number,
): EditableConfidenceColorBand[] {
  if (bands.length <= 1 || !bands[index]) {
    return [...bands];
  }
  const removed = bands[index];
  const remaining = bands
    .filter((_, bandIndex) => bandIndex !== index)
    .map((band) => ({ ...band }));
  if (!removed) {
    return remaining;
  }
  if (index === 0) {
    const first = remaining[0];
    if (first) first.start = removed.start;
  } else {
    const previous = remaining[index - 1];
    if (previous) previous.end = removed.end;
  }
  return remaining;
}
