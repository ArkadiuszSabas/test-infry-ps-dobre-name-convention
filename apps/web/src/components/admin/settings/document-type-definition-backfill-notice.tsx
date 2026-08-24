"use client";

import { AlertTriangleIcon } from "lucide-react";
import { useTranslations } from "next-intl";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import type { DocumentTypeDefinition } from "@/lib/admin-settings/types";

import type { RequiredFieldBackfillBlock } from "./document-type-definition-ui-helpers";

interface RequiredFieldBackfillNoticeProps {
  blocks: readonly RequiredFieldBackfillBlock[];
  onEditDocumentType: (documentType: DocumentTypeDefinition) => void;
}

export function RequiredFieldBackfillNotice({
  blocks,
  onEditDocumentType,
}: RequiredFieldBackfillNoticeProps) {
  const t = useTranslations("AdminSettings.documentTypes.definition.errors");

  return (
    <Alert variant="destructive">
      <AlertTriangleIcon />
      <AlertTitle>{t("requiredBackfillTitle")}</AlertTitle>
      <AlertDescription className="flex flex-col gap-3 text-balance">
        <p>{t("requiredBackfillDescription")}</p>
        <div className="flex flex-col gap-3">
          {blocks.map((block) => (
            <div className="flex flex-col gap-2" key={block.fieldRowId}>
              <p className="font-medium">
                {t("requiredBackfillField", { field: block.fieldLabel })}
              </p>
              {block.isNewField ? (
                <p>{t("requiredBackfillNewFieldHint")}</p>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {block.documentTypes.map((documentType) => (
                    <Button
                      key={documentType.id}
                      onClick={() => onEditDocumentType(documentType)}
                      size="sm"
                      type="button"
                      variant="outline"
                    >
                      {t("editDocumentType", {
                        name: documentType.displayLabel,
                      })}
                    </Button>
                  ))}
                </div>
              )}
              <p>
                {block.documentTypes
                  .map((documentType) => documentType.displayLabel)
                  .join(", ")}
              </p>
            </div>
          ))}
        </div>
      </AlertDescription>
    </Alert>
  );
}
