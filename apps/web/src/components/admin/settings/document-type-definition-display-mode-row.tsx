"use client";

import { ArrowDownIcon, ArrowUpIcon, PlusIcon, Trash2Icon } from "lucide-react";
import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Field,
  FieldContent,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { SystemCatalogDisplayPartSourceType } from "@/lib/admin-settings/types";
import type {
  SystemCatalogDisplayModeDraft,
  SystemCatalogDisplayModePartDraft,
  SystemCatalogFieldDraft,
} from "@/lib/admin-settings/view-model";

import { FieldShell } from "@/components/admin/catalog/catalog-shared";
import {
  moveArrayItem,
  NONE_VALUE,
} from "./document-type-definition-ui-helpers";

interface DisplayModeDraftRowProps {
  disabled: boolean;
  fields: readonly SystemCatalogFieldDraft[];
  isFirst: boolean;
  isLast: boolean;
  mode: SystemCatalogDisplayModeDraft;
  onAddPart: (sourceType: SystemCatalogDisplayPartSourceType) => void;
  onMoveDown: () => void;
  onMoveUp: () => void;
  onRemove: () => void;
  onUpdate: (patch: Partial<SystemCatalogDisplayModeDraft>) => void;
}

export function DisplayModeDraftRow({
  disabled,
  fields,
  isFirst,
  isLast,
  mode,
  onAddPart,
  onMoveDown,
  onMoveUp,
  onRemove,
  onUpdate,
}: DisplayModeDraftRowProps) {
  const t = useTranslations(
    "AdminSettings.documentTypes.definition.displayModes",
  );

  function updatePart(
    partRowId: string,
    patch: Partial<SystemCatalogDisplayModePartDraft>,
  ) {
    onUpdate({
      parts: mode.parts.map((part) =>
        part.rowId === partRowId ? { ...part, ...patch } : part,
      ),
    });
  }

  return (
    <div className="flex flex-col gap-3 rounded-lg border bg-background p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-sm font-semibold">
          {mode.name || t("newMode")}
        </span>
        <div className="flex items-center gap-2">
          <Button
            aria-label={t("moveUp")}
            disabled={disabled || isFirst}
            onClick={onMoveUp}
            size="sm"
            type="button"
            variant="outline"
          >
            <ArrowUpIcon data-icon="inline-start" />
          </Button>
          <Button
            aria-label={t("moveDown")}
            disabled={disabled || isLast}
            onClick={onMoveDown}
            size="sm"
            type="button"
            variant="outline"
          >
            <ArrowDownIcon data-icon="inline-start" />
          </Button>
          <Button
            aria-label={t("remove")}
            disabled={disabled}
            onClick={onRemove}
            size="sm"
            type="button"
            variant="outline"
          >
            <Trash2Icon data-icon="inline-start" />
          </Button>
        </div>
      </div>

      <FieldGroup className="gap-3">
        <FieldShell htmlFor={`${mode.rowId}-name`} label={t("name")}>
          <Input
            disabled={disabled}
            id={`${mode.rowId}-name`}
            onChange={(event) => onUpdate({ name: event.target.value })}
            value={mode.name}
          />
        </FieldShell>
        <div className="grid gap-2 sm:grid-cols-2">
          <CheckboxField
            checked={mode.isDefault}
            disabled={disabled || !mode.isActive}
            id={`${mode.rowId}-default`}
            label={t("default")}
            onChange={(checked) => onUpdate({ isDefault: checked })}
          />
          <CheckboxField
            checked={mode.isActive}
            disabled={disabled}
            id={`${mode.rowId}-active`}
            label={t("active")}
            onChange={(checked) =>
              onUpdate({
                isActive: checked,
                ...(checked ? {} : { isDefault: false }),
              })
            }
          />
        </div>
      </FieldGroup>

      <div className="flex flex-col gap-2">
        <span className="text-xs font-medium text-muted-foreground">
          {t("parts")}
        </span>
        {mode.parts.map((part, partIndex) => (
          <DisplayModePartDraftRow
            disabled={disabled}
            fields={fields}
            isFirst={partIndex === 0}
            isLast={partIndex === mode.parts.length - 1}
            key={part.rowId}
            onMoveDown={() =>
              onUpdate({ parts: moveArrayItem(mode.parts, partIndex, 1) })
            }
            onMoveUp={() =>
              onUpdate({ parts: moveArrayItem(mode.parts, partIndex, -1) })
            }
            onRemove={() =>
              onUpdate({
                parts: mode.parts.filter(
                  (candidate) => candidate.rowId !== part.rowId,
                ),
              })
            }
            onUpdate={(patch) => updatePart(part.rowId, patch)}
            part={part}
          />
        ))}
        <div className="flex flex-wrap gap-2">
          <Button
            disabled={disabled}
            onClick={() => onAddPart("base_name")}
            size="sm"
            type="button"
            variant="outline"
          >
            <PlusIcon data-icon="inline-start" />
            {t("addBaseName")}
          </Button>
          <Button
            disabled={disabled}
            onClick={() => onAddPart("extension_field")}
            size="sm"
            type="button"
            variant="outline"
          >
            <PlusIcon data-icon="inline-start" />
            {t("addFieldPart")}
          </Button>
        </div>
      </div>
    </div>
  );
}

interface DisplayModePartDraftRowProps {
  disabled: boolean;
  fields: readonly SystemCatalogFieldDraft[];
  isFirst: boolean;
  isLast: boolean;
  onMoveDown: () => void;
  onMoveUp: () => void;
  onRemove: () => void;
  onUpdate: (patch: Partial<SystemCatalogDisplayModePartDraft>) => void;
  part: SystemCatalogDisplayModePartDraft;
}

function DisplayModePartDraftRow({
  disabled,
  fields,
  isFirst,
  isLast,
  onMoveDown,
  onMoveUp,
  onRemove,
  onUpdate,
  part,
}: DisplayModePartDraftRowProps) {
  const t = useTranslations("AdminSettings.documentTypes.definition.parts");
  const selectableFields = fields.filter(
    (field) => field.isActive || field.rowId === part.extensionFieldRowId,
  );

  return (
    <div className="grid gap-2 rounded-lg border bg-muted/20 p-2 sm:grid-cols-[1fr_1fr_1fr_auto]">
      <Select
        disabled={disabled}
        onValueChange={(value) =>
          onUpdate({
            extensionFieldRowId:
              value === "base_name" ? null : part.extensionFieldRowId,
            sourceType: value as SystemCatalogDisplayPartSourceType,
          })
        }
        value={part.sourceType}
      >
        <SelectTrigger aria-label={t("sourceType")} className="w-full">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectGroup>
            <SelectItem value="base_name">{t("baseName")}</SelectItem>
            <SelectItem value="extension_field">
              {t("extensionField")}
            </SelectItem>
          </SelectGroup>
        </SelectContent>
      </Select>

      <Select
        disabled={disabled || part.sourceType !== "extension_field"}
        onValueChange={(value) =>
          onUpdate({
            extensionFieldRowId: value === NONE_VALUE ? null : value,
          })
        }
        value={part.extensionFieldRowId ?? NONE_VALUE}
      >
        <SelectTrigger aria-label={t("field")} className="w-full">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectGroup>
            <SelectItem value={NONE_VALUE}>{t("none")}</SelectItem>
            {selectableFields.map((field) => (
              <SelectItem key={field.rowId} value={field.rowId}>
                {field.label || field.code}
              </SelectItem>
            ))}
          </SelectGroup>
        </SelectContent>
      </Select>

      <Input
        aria-label={t("separator")}
        disabled={disabled}
        onChange={(event) => onUpdate({ separatorBefore: event.target.value })}
        placeholder={t("separatorPlaceholder")}
        value={part.separatorBefore}
      />

      <div className="flex items-center gap-2">
        <Button
          aria-label={t("moveUp")}
          disabled={disabled || isFirst}
          onClick={onMoveUp}
          size="sm"
          type="button"
          variant="outline"
        >
          <ArrowUpIcon data-icon="inline-start" />
        </Button>
        <Button
          aria-label={t("moveDown")}
          disabled={disabled || isLast}
          onClick={onMoveDown}
          size="sm"
          type="button"
          variant="outline"
        >
          <ArrowDownIcon data-icon="inline-start" />
        </Button>
        <Button
          aria-label={t("remove")}
          disabled={disabled}
          onClick={onRemove}
          size="sm"
          type="button"
          variant="outline"
        >
          <Trash2Icon data-icon="inline-start" />
        </Button>
      </div>
    </div>
  );
}

interface CheckboxFieldProps {
  checked: boolean;
  disabled: boolean;
  id: string;
  label: string;
  onChange: (checked: boolean) => void;
}

function CheckboxField({
  checked,
  disabled,
  id,
  label,
  onChange,
}: CheckboxFieldProps) {
  return (
    <Field
      className="rounded-lg border bg-muted/20 p-3"
      orientation="horizontal"
    >
      <Checkbox
        checked={checked}
        disabled={disabled}
        id={id}
        onCheckedChange={(value) => onChange(value === true)}
      />
      <FieldContent>
        <FieldLabel htmlFor={id}>{label}</FieldLabel>
      </FieldContent>
    </Field>
  );
}
