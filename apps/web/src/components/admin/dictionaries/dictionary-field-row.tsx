"use client";

import {
  ArrowDownIcon,
  ArrowUpIcon,
  GripVerticalIcon,
  Trash2Icon,
} from "lucide-react";
import { useTranslations } from "next-intl";

import { CatalogFormSection } from "@/components/admin/catalog/catalog-form-section";
import { FieldShell } from "@/components/admin/catalog/catalog-shared";
import {
  Field,
  FieldDescription,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field";
import { IconTooltipButton } from "@/components/ui/icon-tooltip-button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import {
  applyDictionaryFieldTypeOption,
  dictionaryFieldTypeOptions,
  type DictionaryFieldTypeOption,
} from "@/lib/admin-settings/dictionary-field-presets";
import { formatJsonObject } from "@/lib/admin-settings/dictionary-view-model";
import {
  dictionaryFieldFlags,
  getAdvancedSettingCount,
  getCurrentTypeOption,
  getFlagValues,
  isCatalogStatus,
  isDictionaryFieldTypeOption,
  parseOptionalConstraintsObject,
  parseOptionalJsonObject,
  statusOptions,
  type DictionaryFieldFormRow,
  type DictionaryFieldRowProps,
} from "./dictionary-field-row-model";

export function DictionaryFieldRow({
  errors,
  index,
  isPending,
  onDragEnd,
  onDragStart,
  onDrop,
  onMove,
  onRemove,
  onUpdate,
  row,
  rowCount,
}: DictionaryFieldRowProps) {
  const t = useTranslations("AdminSettings.customDictionaries.fieldsForm");
  const common = useTranslations("AdminSettings.common");
  const canReorder = rowCount > 1 && !isPending;

  return (
    <div
      className="flex flex-col gap-4 rounded-lg border bg-muted/10 p-4"
      onDragOver={(event) => {
        if (canReorder) {
          event.preventDefault();
          event.dataTransfer.dropEffect = "move";
        }
      }}
      onDrop={(event) => {
        if (canReorder) {
          event.preventDefault();
          onDrop();
        }
      }}
    >
      <div className="flex items-start gap-3">
        <IconTooltipButton
          aria-label={t("order.drag", { number: index + 1 })}
          className="cursor-grab active:cursor-grabbing"
          disabled={!canReorder}
          draggable={canReorder}
          onDragEnd={onDragEnd}
          onDragStart={(event) => {
            event.dataTransfer.effectAllowed = "move";
            onDragStart();
          }}
          tooltip={t("order.drag", { number: index + 1 })}
          type="button"
          variant="ghost"
        >
          <GripVerticalIcon />
        </IconTooltipButton>

        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium">
            {row.label || t("rowTitle", { number: index + 1 })}
          </p>
          <p className="text-xs text-muted-foreground">
            {t("order.position", { number: index + 1 })}
          </p>
        </div>

        <div className="flex shrink-0 gap-1">
          <IconTooltipButton
            aria-label={t("order.moveUp", { number: index + 1 })}
            disabled={!canReorder || index === 0}
            onClick={() => onMove(row.rowId, -1)}
            tooltip={t("order.moveUp", { number: index + 1 })}
            type="button"
            variant="secondary"
          >
            <ArrowUpIcon />
          </IconTooltipButton>
          <IconTooltipButton
            aria-label={t("order.moveDown", { number: index + 1 })}
            disabled={!canReorder || index === rowCount - 1}
            onClick={() => onMove(row.rowId, 1)}
            tooltip={t("order.moveDown", { number: index + 1 })}
            type="button"
            variant="secondary"
          >
            <ArrowDownIcon />
          </IconTooltipButton>
          <IconTooltipButton
            aria-label={t("remove")}
            disabled={isPending}
            onClick={() => onRemove(row.rowId)}
            tooltip={t("remove")}
            type="button"
            variant="secondary"
          >
            <Trash2Icon />
          </IconTooltipButton>
        </div>
      </div>

      <FieldGroup className="gap-4">
        <FieldShell
          description={t("fields.labelDescription")}
          error={errors.label}
          htmlFor={`field-${row.rowId}-label`}
          label={t("fields.label")}
          required
          requiredLabel={common("requiredField")}
        >
          <Input
            aria-invalid={Boolean(errors.label)}
            disabled={isPending}
            id={`field-${row.rowId}-label`}
            onChange={(event) =>
              update(row.rowId, (current) => ({
                ...current,
                label: event.target.value,
              }))
            }
            value={row.label}
          />
        </FieldShell>

        <div className="grid gap-4 md:grid-cols-2">
          <Field>
            <FieldLabel>{t("fields.dataType")}</FieldLabel>
            <FieldDescription>
              {t("fields.dataTypeDescription")}
            </FieldDescription>
            <Select
              disabled={isPending}
              onValueChange={(value) => {
                if (isDictionaryFieldTypeOption(value)) {
                  applyTypeOption(value);
                }
              }}
              value={getCurrentTypeOption(row)}
            >
              <SelectTrigger className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectGroup>
                  {dictionaryFieldTypeOptions.map((dataType) => (
                    <SelectItem key={dataType} value={dataType}>
                      {t(`dataTypes.${dataType}`)}
                    </SelectItem>
                  ))}
                </SelectGroup>
              </SelectContent>
            </Select>
          </Field>

          <Field>
            <FieldLabel>{t("fields.status")}</FieldLabel>
            <FieldDescription>{t("fields.statusDescription")}</FieldDescription>
            <ToggleGroup
              aria-label={t("fields.status")}
              onValueChange={(value) => {
                if (isCatalogStatus(value)) {
                  update(row.rowId, (current) => ({
                    ...current,
                    status: value,
                  }));
                }
              }}
              type="single"
              value={row.status}
              variant="outline"
            >
              {statusOptions.map((status) => (
                <ToggleGroupItem
                  disabled={isPending}
                  key={status}
                  size="sm"
                  value={status}
                >
                  {common(`status.${status}`)}
                </ToggleGroupItem>
              ))}
            </ToggleGroup>
          </Field>
        </div>

        <Field>
          <FieldLabel>{t("fields.flags")}</FieldLabel>
          <FieldDescription>{t("fields.flagsDescription")}</FieldDescription>
          <ToggleGroup
            aria-label={t("fields.flags")}
            onValueChange={(values) => {
              const selected = new Set(values);
              update(row.rowId, (current) => ({
                ...current,
                isUnique: selected.has("unique"),
                required: selected.has("required"),
              }));
            }}
            type="multiple"
            value={getFlagValues(row)}
            variant="outline"
          >
            {dictionaryFieldFlags.map((flag) => (
              <ToggleGroupItem
                disabled={isPending}
                key={flag}
                size="sm"
                value={flag}
              >
                {t(`flags.${flag}`)}
              </ToggleGroupItem>
            ))}
          </ToggleGroup>
        </Field>

        <CatalogFormSection
          description={t("integration.description")}
          summary={
            <span className="font-mono">
              {row.externalId || t("integration.generated")}
            </span>
          }
          title={t("integration.title")}
        >
          <FieldShell
            description={t("integration.externalIdDescription")}
            error={errors.externalId}
            htmlFor={`field-${row.rowId}-external-id`}
            label={t("fields.externalId")}
          >
            <Input
              aria-invalid={Boolean(errors.externalId)}
              disabled={isPending}
              id={`field-${row.rowId}-external-id`}
              onChange={(event) =>
                update(row.rowId, (current) => ({
                  ...current,
                  externalId: event.target.value,
                }))
              }
              placeholder={t("integration.externalIdPlaceholder")}
              value={row.externalId}
            />
          </FieldShell>
        </CatalogFormSection>

        <CatalogFormSection
          contentClassName="flex flex-col gap-4"
          summary={t("advanced.summary", {
            count: getAdvancedSettingCount(row),
          })}
          title={t("advanced.title")}
        >
          <FieldShell
            description={t("advanced.constraintsDescription")}
            error={errors.constraints}
            htmlFor={`field-${row.rowId}-constraints`}
            label={t("fields.constraints")}
          >
            <Textarea
              aria-invalid={Boolean(errors.constraints)}
              disabled={isPending}
              id={`field-${row.rowId}-constraints`}
              onChange={(event) =>
                update(row.rowId, (current) => ({
                  ...current,
                  constraintsText: event.target.value,
                }))
              }
              placeholder='{"max_length": 32}'
              value={row.constraintsText}
            />
          </FieldShell>

          <FieldShell
            description={t("advanced.normalizationDescription")}
            error={errors.normalization}
            htmlFor={`field-${row.rowId}-normalization`}
            label={t("fields.normalization")}
          >
            <Textarea
              aria-invalid={Boolean(errors.normalization)}
              disabled={isPending}
              id={`field-${row.rowId}-normalization`}
              onChange={(event) =>
                update(row.rowId, (current) => ({
                  ...current,
                  normalizationText: event.target.value,
                }))
              }
              placeholder='{"trim": true}'
              value={row.normalizationText}
            />
          </FieldShell>

          <FieldShell
            description={t("advanced.formatDescription")}
            error={errors.format}
            htmlFor={`field-${row.rowId}-format`}
            label={t("fields.format")}
          >
            <Textarea
              aria-invalid={Boolean(errors.format)}
              disabled={isPending}
              id={`field-${row.rowId}-format`}
              onChange={(event) =>
                update(row.rowId, (current) => ({
                  ...current,
                  formatText: event.target.value,
                }))
              }
              placeholder='{"example": "FIN"}'
              value={row.formatText}
            />
          </FieldShell>
        </CatalogFormSection>
      </FieldGroup>
    </div>
  );

  function applyTypeOption(option: DictionaryFieldTypeOption) {
    update(row.rowId, (current) => {
      const nextType = applyDictionaryFieldTypeOption(option, {
        constraints: parseOptionalConstraintsObject(current.constraintsText),
        format: parseOptionalJsonObject(current.formatText),
      });

      return {
        ...current,
        constraintsText: formatJsonObject(nextType.constraints),
        dataType: nextType.dataType,
        formatText: formatJsonObject(nextType.format),
      };
    });
  }

  function update(
    rowId: string,
    updater: (row: DictionaryFieldFormRow) => DictionaryFieldFormRow,
  ) {
    onUpdate(rowId, updater);
  }
}
