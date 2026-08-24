"use client";

import { Edit3Icon, PowerIcon, Settings2Icon, Trash2Icon } from "lucide-react";
import { useTranslations } from "next-intl";

import { IconTooltipButton } from "@/components/ui/icon-tooltip-button";
import { Link } from "@/i18n/navigation";
import type { DocumentTypeDefinition } from "@/lib/admin-settings/types";

interface DocumentTypeCardActionsProps {
  documentType: DocumentTypeDefinition;
  onDeactivate: (documentType: DocumentTypeDefinition) => void;
  onDelete: (documentType: DocumentTypeDefinition) => void;
  onEdit: (documentType: DocumentTypeDefinition) => void;
}

export function DocumentTypeCardActions({
  documentType,
  onDeactivate,
  onDelete,
  onEdit,
}: DocumentTypeCardActionsProps) {
  const t = useTranslations("AdminSettings.documentTypes");
  const label = documentType.displayLabel;

  return (
    <div className="flex justify-end gap-1">
      <IconTooltipButton
        asChild
        aria-label={t("actions.configureMatrix", {
          name: label,
        })}
        tooltip={t("actions.configureMatrix", {
          name: label,
        })}
        variant="secondary"
      >
        <Link
          href={`/admin/dictionaries/attribute-matrix?documentTypeId=${documentType.id}`}
        >
          <Settings2Icon />
        </Link>
      </IconTooltipButton>
      <IconTooltipButton
        aria-label={t("actions.edit", { name: label })}
        onClick={() => onEdit(documentType)}
        tooltip={t("actions.edit", { name: label })}
        type="button"
        variant="secondary"
      >
        <Edit3Icon />
      </IconTooltipButton>
      <IconTooltipButton
        aria-label={t("actions.deactivate", { name: label })}
        disabled={documentType.status === "inactive"}
        onClick={() => onDeactivate(documentType)}
        tooltip={t("actions.deactivate", { name: label })}
        type="button"
        variant="secondary"
      >
        <PowerIcon />
      </IconTooltipButton>
      <IconTooltipButton
        aria-label={t("actions.delete", { name: label })}
        onClick={() => onDelete(documentType)}
        tooltip={t("actions.delete", { name: label })}
        type="button"
        variant="secondary"
      >
        <Trash2Icon />
      </IconTooltipButton>
    </div>
  );
}
