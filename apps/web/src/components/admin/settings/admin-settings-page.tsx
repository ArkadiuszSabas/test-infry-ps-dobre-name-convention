"use client";

import { BracesIcon, FileTextIcon, Settings2Icon } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/ui/page-header";
import { PageBackLink } from "@/components/ui/page-back-link";
import { PageShell } from "@/components/ui/page-shell";

import { AttributeCatalog } from "./attribute-catalog";
import { AttributeMatrixEditor } from "./attribute-matrix-editor";
import { DocumentTypeCatalog } from "./document-type-catalog";

type AdminSettingsTab = "documentTypes" | "attributes" | "attributeMatrix";

const tabs = [
  { icon: FileTextIcon, id: "documentTypes" },
  { icon: BracesIcon, id: "attributes" },
  { icon: Settings2Icon, id: "attributeMatrix" },
] as const satisfies readonly {
  icon: typeof FileTextIcon;
  id: AdminSettingsTab;
}[];

export function AdminSettingsPage() {
  const t = useTranslations("AdminSettings");
  const [activeTab, setActiveTab] = useState<AdminSettingsTab>("documentTypes");

  return (
    <PageShell
      navigation={<PageBackLink href="/admin">{t("back")}</PageBackLink>}
    >
      <PageHeader
        description={t("description")}
        icon={Settings2Icon}
        title={t("title")}
      />

      <div className="grid gap-3 md:grid-cols-3" role="tablist">
        {tabs.map((tab) => {
          const Icon = tab.icon;

          return (
            <Button
              aria-controls={`${tab.id}-panel`}
              aria-selected={activeTab === tab.id}
              className="h-auto justify-start gap-3 px-4 py-3 text-left"
              id={`${tab.id}-tab`}
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              role="tab"
              type="button"
              variant={activeTab === tab.id ? "primary" : "outline"}
            >
              <Icon data-icon="inline-start" />
              {t(`tabs.${tab.id}`)}
            </Button>
          );
        })}
      </div>

      <div
        aria-labelledby={`${activeTab}-tab`}
        id={`${activeTab}-panel`}
        role="tabpanel"
      >
        {activeTab === "documentTypes" ? (
          <DocumentTypeCatalog />
        ) : activeTab === "attributes" ? (
          <AttributeCatalog />
        ) : (
          <AttributeMatrixEditor />
        )}
      </div>
    </PageShell>
  );
}
