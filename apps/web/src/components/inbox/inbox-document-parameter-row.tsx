"use client";

import { useTranslations } from "next-intl";

import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { Field, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type {
  DocumentParameterControlKind,
  DocumentParameterItem,
  DocumentParameterSection,
} from "@/lib/inbox/view-model";
import { cn } from "@/lib/utils";

export interface DictionaryLookupState {
  isError: boolean;
  isPending: boolean;
}

interface DocumentParameterGroupProps {
  dictionaryStateById: ReadonlyMap<string, DictionaryLookupState>;
  section: DocumentParameterSection;
}

export function DocumentParameterGroup({
  dictionaryStateById,
  section,
}: DocumentParameterGroupProps) {
  const t = useTranslations("Inbox.detail.parameters");

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between gap-3">
        <h3 className="text-sm font-medium">
          {t(`groups.${section.requirement}`)}
        </h3>
        <span className="text-xs text-muted-foreground">
          {t("groupCount", { count: section.items.length })}
        </span>
      </div>
      <div className="flex flex-col gap-3">
        {section.items.map((item) => (
          <DocumentParameterRow
            dictionaryState={
              item.field.dictionaryId
                ? dictionaryStateById.get(item.field.dictionaryId)
                : undefined
            }
            item={item}
            key={item.field.key}
          />
        ))}
      </div>
    </div>
  );
}

interface DocumentParameterRowProps {
  dictionaryState: DictionaryLookupState | undefined;
  item: DocumentParameterItem;
}

function DocumentParameterRow({
  dictionaryState,
  item,
}: DocumentParameterRowProps) {
  const t = useTranslations("Inbox.detail.parameters");
  const isRequiredMissing = item.requirement === "required" && item.missing;
  const description = parameterDescription(item, dictionaryState, t);

  return (
    <div
      className={cn(
        "flex flex-col gap-3 rounded-lg border bg-muted/10 p-3",
        isRequiredMissing && "border-destructive/50 bg-destructive/5",
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate text-sm font-medium">{item.field.label}</p>
          <p className="mt-1 text-xs text-muted-foreground">
            {item.field.category}
            {" \u00b7 "}
            {t(`types.${item.typeKind}`)}
          </p>
        </div>
        <div className="flex shrink-0 flex-wrap justify-end gap-1">
          <Badge
            variant={item.requirement === "required" ? "secondary" : "outline"}
          >
            {t(`requirements.${item.requirement}`)}
          </Badge>
          {item.field.valueSource === "dictionary" ? (
            <Badge variant="outline">{t("sources.dictionary")}</Badge>
          ) : null}
        </div>
      </div>

      <DocumentParameterControl invalid={isRequiredMissing} item={item} />

      {description ? (
        <p
          className={cn(
            "text-xs text-muted-foreground",
            (isRequiredMissing || dictionaryState?.isError) &&
              "font-medium text-destructive",
          )}
          role={
            isRequiredMissing || dictionaryState?.isError ? "alert" : undefined
          }
        >
          {description}
        </p>
      ) : null}
    </div>
  );
}

interface DocumentParameterControlProps {
  invalid: boolean;
  item: DocumentParameterItem;
}

function DocumentParameterControl({
  invalid,
  item,
}: DocumentParameterControlProps) {
  const t = useTranslations("Inbox.detail.parameters");
  const fieldId = `document-parameter-${toDomId(item.field.key)}`;

  if (item.controlKind === "select") {
    return (
      <Field data-invalid={invalid}>
        <FieldLabel className="sr-only" htmlFor={fieldId}>
          {item.field.label}
        </FieldLabel>
        <Select disabled value={item.inputValue || undefined}>
          <SelectTrigger aria-invalid={invalid} className="w-full" id={fieldId}>
            <SelectValue placeholder={t("notProvided")} />
          </SelectTrigger>
          <SelectContent>
            <SelectGroup>
              {item.options.map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectGroup>
          </SelectContent>
        </Select>
      </Field>
    );
  }

  if (item.controlKind === "checkbox") {
    return (
      <Field data-invalid={invalid} orientation="horizontal">
        <Checkbox
          aria-invalid={invalid}
          checked={item.value === true}
          disabled
          id={fieldId}
        />
        <FieldLabel className="font-normal" htmlFor={fieldId}>
          {item.value === true
            ? t("boolean.true")
            : item.value === false
              ? t("boolean.false")
              : t("notProvided")}
        </FieldLabel>
      </Field>
    );
  }

  return (
    <Field data-invalid={invalid}>
      <FieldLabel className="sr-only" htmlFor={fieldId}>
        {item.field.label}
      </FieldLabel>
      <Input
        aria-invalid={invalid}
        aria-readonly="true"
        id={fieldId}
        placeholder={t("notProvided")}
        readOnly
        type={inputTypeForControl(item.controlKind)}
        value={item.inputValue}
      />
    </Field>
  );
}

function parameterDescription(
  item: DocumentParameterItem,
  dictionaryState: DictionaryLookupState | undefined,
  t: (key: string, values?: Record<string, number>) => string,
): string | null {
  if (item.requirement === "required" && item.missing) {
    return t("missingRequired");
  }

  if (item.requirement === "optional" && item.missing) {
    return t("missingOptional");
  }

  if (item.controlKind === "unsupported") {
    return t("unsupportedType");
  }

  if (item.field.valueSource === "dictionary" && dictionaryState?.isError) {
    return t("dictionaryError");
  }

  if (item.field.valueSource === "dictionary" && dictionaryState?.isPending) {
    return t("dictionaryLoading");
  }

  return null;
}

function inputTypeForControl(
  controlKind: DocumentParameterControlKind,
): "date" | "datetime-local" | "number" | "text" {
  if (controlKind === "date") {
    return "date";
  }

  if (controlKind === "datetime") {
    return "datetime-local";
  }

  if (controlKind === "number") {
    return "number";
  }

  return "text";
}

function toDomId(value: string): string {
  return value.replace(/[^a-zA-Z0-9_-]+/gu, "-");
}
