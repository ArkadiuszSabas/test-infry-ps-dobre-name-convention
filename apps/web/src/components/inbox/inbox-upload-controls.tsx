"use client";

import { FileUpIcon, FolderOpenIcon, UploadIcon, XIcon } from "lucide-react";
import { useTranslations } from "next-intl";
import { useRef, useState, type DragEvent, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import {
  Field,
  FieldDescription,
  FieldGroup,
  FieldLabel,
  FieldLegend,
  FieldSet,
} from "@/components/ui/field";
import { IconFrame } from "@/components/ui/icon-frame";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { Spinner } from "@/components/ui/spinner";
import { SystemCatalogSelectCard } from "@/components/system-catalogs/system-catalog-select-card";
import type { DocumentTypeDisplayItem } from "@/lib/system-catalogs/document-type-display";
import type { SystemCatalogDefinition } from "@/lib/system-catalogs/types";
import type {
  ManualUploadDictionaryEntry,
  ManualUploadMetadataField,
  ManualUploadMetadataValue,
} from "@/lib/inbox/types";
import { buildMetadataValues } from "@/lib/inbox/upload-metadata-values";
import { cn } from "@/lib/utils";

import { InboxNotice } from "./inbox-notice";
import { ManualUploadMetadataSection } from "./inbox-upload-metadata";

export interface InboxUploadControlsProps {
  activeDocumentTypeId: string;
  dictionaryOptionsById: Record<string, readonly ManualUploadDictionaryEntry[]>;
  documentTypeDefinition: SystemCatalogDefinition | null;
  documentTypeOptions: readonly DocumentTypeDisplayItem[];
  hasOptionsError: boolean;
  isOptionsPending: boolean;
  isOpen: boolean;
  isUploading: boolean;
  metadataFields: readonly ManualUploadMetadataField[];
  onDocumentTypeChange: (documentTypeId: string) => void;
  onOpenChange: (open: boolean) => void;
  onUpload: (draft: {
    file: File;
    metadataValues: Record<string, ManualUploadMetadataValue>;
  }) => void;
  optionsError: string | null;
  uploadError: string | null;
  uploadDisabled: boolean;
}

export function InboxUploadControls({
  activeDocumentTypeId,
  dictionaryOptionsById,
  documentTypeDefinition,
  documentTypeOptions,
  hasOptionsError,
  isOptionsPending,
  isOpen,
  isUploading,
  metadataFields,
  onDocumentTypeChange,
  onOpenChange,
  onUpload,
  optionsError,
  uploadError,
  uploadDisabled,
}: InboxUploadControlsProps) {
  const t = useTranslations("Inbox");
  const collection = useTranslations("CollectionView");
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDraggingFile, setIsDraggingFile] = useState(false);
  const [metadataDraft, setMetadataDraft] = useState<Record<string, string>>(
    {},
  );
  const [metadataErrors, setMetadataErrors] = useState<Record<string, string>>(
    {},
  );
  const hasDocumentTypeOptions = documentTypeOptions.length > 0;
  const documentTypeSelectDisabled =
    isOptionsPending || isUploading || !hasDocumentTypeOptions;
  const hasRequiredMetadata = metadataFields.every(
    (field) =>
      !field.required || (metadataDraft[field.key]?.trim().length ?? 0) > 0,
  );
  const submitDisabled =
    uploadDisabled ||
    isUploading ||
    hasOptionsError ||
    !selectedFile ||
    !activeDocumentTypeId ||
    !hasRequiredMetadata;
  const triggerDisabled = isOptionsPending || hasOptionsError || isUploading;
  const filePickerDisabled = uploadDisabled || isUploading;
  const requiredMetadataFields = metadataFields.filter(
    (field) => field.required,
  );
  const optionalMetadataFields = metadataFields.filter(
    (field) => !field.required,
  );

  function resetDraft() {
    setSelectedFile(null);
    setIsDraggingFile(false);
    setMetadataDraft({});
    setMetadataErrors({});

    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  }

  function handleOpenChange(open: boolean) {
    if (!open && isUploading) {
      return;
    }

    resetDraft();
    onOpenChange(open);
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (submitDisabled || !selectedFile) {
      return;
    }

    const metadataValues = buildMetadataValues({
      fields: metadataFields,
      messages: {
        integer: t("upload.metadata.errors.integer"),
        number: t("upload.metadata.errors.number"),
        required: t("upload.metadata.errors.required"),
      },
      values: metadataDraft,
    });

    if (metadataValues.errors) {
      setMetadataErrors(metadataValues.errors);
      return;
    }

    setMetadataErrors({});
    onUpload({ file: selectedFile, metadataValues: metadataValues.values });
  }

  function handleFileDrop(event: DragEvent<HTMLButtonElement>) {
    event.preventDefault();
    setIsDraggingFile(false);

    if (filePickerDisabled) {
      return;
    }

    const file = event.dataTransfer.files.item(0);

    if (file) {
      setSelectedFile(file);
    }
  }

  function handleFileDrag(event: DragEvent<HTMLButtonElement>) {
    event.preventDefault();

    if (filePickerDisabled) {
      return;
    }

    event.dataTransfer.dropEffect = "copy";
    setIsDraggingFile(true);
  }

  function handleFileDragLeave(event: DragEvent<HTMLButtonElement>) {
    event.preventDefault();
    setIsDraggingFile(false);
  }

  function handleMetadataChange(
    field: ManualUploadMetadataField,
    value: string,
  ) {
    setMetadataDraft((current) => ({
      ...current,
      [field.key]: value,
    }));
    setMetadataErrors((current) => ({
      ...current,
      [field.key]: "",
    }));
  }

  return (
    <Sheet onOpenChange={handleOpenChange} open={isOpen}>
      <SheetTrigger asChild>
        <Button disabled={triggerDisabled} type="button">
          <UploadIcon data-icon="inline-start" />
          {t("upload.action")}
        </Button>
      </SheetTrigger>

      <SheetContent
        className="data-[side=right]:w-full data-[side=right]:sm:max-w-xl"
        side="right"
      >
        <form className="flex min-h-0 flex-1 flex-col" onSubmit={handleSubmit}>
          <SheetHeader className="border-b px-5 py-4 pr-12">
            <SheetTitle>{t("upload.drawerTitle")}</SheetTitle>
            <SheetDescription>{t("upload.drawerDescription")}</SheetDescription>
          </SheetHeader>

          <div className="flex flex-1 flex-col gap-5 overflow-y-auto p-5">
            {optionsError ? (
              <InboxNotice title={optionsError} tone="danger" />
            ) : null}
            {uploadError ? (
              <InboxNotice title={uploadError} tone="danger" />
            ) : null}
            {!hasDocumentTypeOptions ? (
              <InboxNotice title={t("upload.noActiveDocumentTypes")} />
            ) : null}

            <FieldGroup>
              <SystemCatalogSelectCard
                catalogKey="document_type"
                definition={documentTypeDefinition}
                description={t("upload.documentTypeCard.description")}
                disabled={documentTypeSelectDisabled}
                labels={{
                  displayModeLabel: t("upload.documentTypeCard.displayMode"),
                  displayModePlaceholder: t(
                    "upload.documentTypeCard.displayModePlaceholder",
                  ),
                  noOptions: t("upload.noActiveDocumentTypes"),
                  searchPlaceholder: collection("search"),
                  valueLabel: t("upload.documentTypeLabel"),
                  valuePlaceholder: t("upload.documentTypePlaceholder"),
                }}
                onValueChange={(value) => {
                  setMetadataDraft({});
                  setMetadataErrors({});
                  onDocumentTypeChange(value);
                }}
                options={documentTypeOptions}
                title={t("upload.documentTypeCard.title")}
                value={activeDocumentTypeId}
              />

              <Field>
                <FieldLabel>{t("upload.file.label")}</FieldLabel>
                <Button
                  aria-label={t("upload.file.choose")}
                  className={cn(
                    "h-auto min-h-44 w-full justify-center rounded-xl border-dashed px-5 py-6 shadow-none transition-colors",
                    "hover:border-primary/40 hover:bg-accent/50",
                    isDraggingFile &&
                      "border-primary bg-primary/5 ring-2 ring-primary/20",
                  )}
                  disabled={filePickerDisabled}
                  onClick={() => fileInputRef.current?.click()}
                  onDragEnter={handleFileDrag}
                  onDragLeave={handleFileDragLeave}
                  onDragOver={handleFileDrag}
                  onDrop={handleFileDrop}
                  type="button"
                  variant="outline"
                >
                  <span className="flex min-w-0 flex-col items-center gap-4 text-center">
                    <IconFrame
                      className={cn(
                        selectedFile && "bg-primary text-primary-foreground",
                      )}
                      icon={FileUpIcon}
                      size="lg"
                    />
                    <span className="flex max-w-full flex-col gap-1">
                      <span className="truncate text-base font-medium">
                        {selectedFile?.name ?? t("upload.file.dropTitle")}
                      </span>
                      <span
                        aria-live="polite"
                        className="text-sm font-normal text-muted-foreground"
                      >
                        {selectedFile
                          ? t("upload.file.selected", {
                              size: formatFileSize(selectedFile.size),
                            })
                          : t("upload.file.dropDescription")}
                      </span>
                    </span>
                    <span className="inline-flex items-center gap-2 rounded-md border bg-background px-3 py-2 text-sm font-medium shadow-xs">
                      <FolderOpenIcon data-icon="inline-start" />
                      {t("upload.file.choose")}
                    </span>
                  </span>
                </Button>
                <FieldDescription>
                  {t("upload.file.emptyDescription")}
                </FieldDescription>
                <input
                  id="manual-upload-file"
                  ref={fileInputRef}
                  aria-label={t("upload.fileInputLabel")}
                  accept="application/pdf,.pdf"
                  aria-hidden="true"
                  className="sr-only"
                  disabled={filePickerDisabled}
                  onChange={(event) => {
                    setSelectedFile(event.target.files?.[0] ?? null);
                  }}
                  tabIndex={-1}
                  type="file"
                />
              </Field>

              {metadataFields.length > 0 ? (
                <FieldSet>
                  <FieldLegend>{t("upload.metadata.title")}</FieldLegend>
                  <FieldGroup>
                    <ManualUploadMetadataSection
                      dictionaryOptionsById={dictionaryOptionsById}
                      disabled={isUploading}
                      errors={metadataErrors}
                      fields={requiredMetadataFields}
                      onChange={handleMetadataChange}
                      requirement="required"
                      values={metadataDraft}
                    />
                    <ManualUploadMetadataSection
                      dictionaryOptionsById={dictionaryOptionsById}
                      disabled={isUploading}
                      errors={metadataErrors}
                      fields={optionalMetadataFields}
                      onChange={handleMetadataChange}
                      requirement="optional"
                      values={metadataDraft}
                    />
                  </FieldGroup>
                </FieldSet>
              ) : null}
            </FieldGroup>
          </div>

          <SheetFooter className="border-t bg-background px-5 py-4 sm:flex-row sm:justify-end">
            <Button
              disabled={isUploading}
              onClick={() => handleOpenChange(false)}
              type="button"
              variant="outline"
            >
              <XIcon data-icon="inline-start" />
              {t("upload.cancel")}
            </Button>
            <Button disabled={submitDisabled} type="submit">
              {isUploading ? (
                <Spinner data-icon="inline-start" />
              ) : (
                <UploadIcon data-icon="inline-start" />
              )}
              {isUploading ? t("upload.uploading") : t("upload.submit")}
            </Button>
          </SheetFooter>
        </form>
      </SheetContent>
    </Sheet>
  );
}

function formatFileSize(size: number) {
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${Math.round(size / 1024)} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}
