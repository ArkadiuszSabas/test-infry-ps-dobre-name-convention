"use client";

import {
  BracesIcon,
  FileTextIcon,
  ListTreeIcon,
  Settings2Icon,
} from "lucide-react";
import { useTranslations } from "next-intl";

import { PageHeader } from "@/components/ui/page-header";
import { PageBackLink } from "@/components/ui/page-back-link";
import { PageShell } from "@/components/ui/page-shell";

import { AttributeCatalog } from "../settings/attribute-catalog";
import { AttributeCategoryCatalog } from "../settings/attribute-category-catalog";
import { AttributeMatrixEditor } from "../settings/attribute-matrix-editor";
import { DocumentTypeCatalog } from "../settings/document-type-catalog";

export type AdminDictionaryId =
  | "attributeCategories"
  | "attributeMatrix"
  | "attributes"
  | "documentTypes";

const dictionaryIcons = {
  attributeCategories: ListTreeIcon,
  attributeMatrix: Settings2Icon,
  attributes: BracesIcon,
  documentTypes: FileTextIcon,
} as const satisfies Record<AdminDictionaryId, typeof FileTextIcon>;

interface AdminDictionaryPageProps {
  dictionaryId: AdminDictionaryId;
  initialDocumentTypeId?: string | null;
}

export function AdminDictionaryPage({
  dictionaryId,
  initialDocumentTypeId = null,
}: AdminDictionaryPageProps) {
  const t = useTranslations("AdminDictionaries");
  const Icon = dictionaryIcons[dictionaryId];

  return (
    <PageShell
      navigation={
        <PageBackLink href="/admin/dictionaries">
          {t("detailBack")}
        </PageBackLink>
      }
    >
      <PageHeader
        description={t(`entries.${dictionaryId}.description`)}
        icon={Icon}
        title={t(`entries.${dictionaryId}.title`)}
      />

      {dictionaryId === "documentTypes" ? (
        <DocumentTypeCatalog />
      ) : dictionaryId === "attributeCategories" ? (
        <AttributeCategoryCatalog />
      ) : dictionaryId === "attributes" ? (
        <AttributeCatalog />
      ) : (
        <AttributeMatrixEditor initialDocumentTypeId={initialDocumentTypeId} />
      )}
    </PageShell>
  );
}
