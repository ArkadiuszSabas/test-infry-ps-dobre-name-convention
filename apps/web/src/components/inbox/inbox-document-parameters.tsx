"use client";

import { useQueries } from "@tanstack/react-query";
import { useTranslations } from "next-intl";

import {
  DocumentParameterGroup,
  type DictionaryLookupState,
} from "@/components/inbox/inbox-document-parameter-row";
import { InboxNotice } from "@/components/inbox/inbox-notice";
import { Badge } from "@/components/ui/badge";
import { Spinner } from "@/components/ui/spinner";
import {
  dictionaryLookupEntriesQueryOptions,
  dictionaryLookupEntryQueryOptions,
} from "@/lib/inbox/query-options";
import type {
  DictionaryLookupEntry,
  DocumentMetadataSchemaEnvelope,
  DocumentMetadataSchemaField,
  InboxDocument,
  ManualUploadDictionaryEntry,
  MetadataScalar,
} from "@/lib/inbox/types";
import { buildDocumentParameterSections } from "@/lib/inbox/view-model";

export interface DocumentParametersState {
  isError: boolean;
  isPending: boolean;
  metadataSchema: DocumentMetadataSchemaEnvelope | null;
}

interface DocumentParametersSectionProps {
  document: InboxDocument;
  state: DocumentParametersState;
}

interface StoredDictionaryValue {
  dictionaryId: string;
  externalId: string;
}

export function DocumentParametersSection({
  document,
  state,
}: DocumentParametersSectionProps) {
  const t = useTranslations("Inbox");
  const fields = state.metadataSchema?.data.fields ?? [];
  const dictionaryIds = getDictionaryIds(fields);
  const dictionaryQueries = useQueries({
    queries: dictionaryIds.map((dictionaryId) =>
      dictionaryLookupEntriesQueryOptions(
        dictionaryId,
        Boolean(state.metadataSchema),
      ),
    ),
  });
  const storedDictionaryValues = getStoredDictionaryValues(
    fields,
    document.metadataValues,
  );
  const storedDictionaryQueries = useQueries({
    queries: storedDictionaryValues.map((value) =>
      dictionaryLookupEntryQueryOptions(
        value.dictionaryId,
        value.externalId,
        Boolean(state.metadataSchema),
      ),
    ),
  });
  const dictionaryOptionsById = new Map<
    string,
    readonly DictionaryLookupEntry[]
  >();
  const dictionaryStateById = new Map<string, DictionaryLookupState>();

  dictionaryIds.forEach((dictionaryId, index) => {
    const query = dictionaryQueries[index];
    dictionaryStateById.set(dictionaryId, {
      isError: query?.isError ?? false,
      isPending: query?.isPending ?? false,
    });

    if (query?.data) {
      dictionaryOptionsById.set(dictionaryId, query.data.data.entries);
    }
  });

  storedDictionaryValues.forEach((value, index) => {
    const query = storedDictionaryQueries[index];
    const currentState = dictionaryStateById.get(value.dictionaryId);
    dictionaryStateById.set(value.dictionaryId, {
      isError: Boolean(currentState?.isError || query?.isError),
      isPending: Boolean(currentState?.isPending || query?.isPending),
    });

    if (query?.data) {
      dictionaryOptionsById.set(
        value.dictionaryId,
        mergeDictionaryEntries(
          dictionaryOptionsById.get(value.dictionaryId) ?? [],
          query.data,
        ),
      );
    }
  });

  const sections = state.metadataSchema
    ? buildDocumentParameterSections({
        dictionaryOptionsById,
        fields,
        values: document.metadataValues,
      })
    : [];

  return (
    <section className="flex flex-col gap-3">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="text-xs font-medium uppercase text-muted-foreground">
            {t("detail.sections.parameters")}
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            {t("detail.parameters.description")}
          </p>
        </div>
        {state.metadataSchema ? (
          <Badge variant="outline">
            {t("detail.parameters.count", {
              count: state.metadataSchema.meta.fieldCount,
            })}
          </Badge>
        ) : null}
      </div>

      {state.isPending ? (
        <div className="flex items-center gap-2 rounded-lg border bg-muted/10 p-3 text-sm text-muted-foreground">
          <Spinner className="size-4" />
          {t("detail.parameters.loading")}
        </div>
      ) : null}

      {state.isError ? (
        <InboxNotice
          description={t("detail.parameters.loadErrorDescription")}
          title={t("detail.parameters.loadErrorTitle")}
          tone="danger"
        />
      ) : null}

      {!state.isPending && !state.isError && sections.length === 0 ? (
        <div className="rounded-lg border bg-muted/10 p-3 text-sm text-muted-foreground">
          {t("detail.parameters.empty")}
        </div>
      ) : null}

      <div className="flex flex-col gap-4">
        {sections.map((section) => (
          <DocumentParameterGroup
            dictionaryStateById={dictionaryStateById}
            key={section.requirement}
            section={section}
          />
        ))}
      </div>
    </section>
  );
}

function getDictionaryIds(
  fields: readonly DocumentMetadataSchemaField[],
): string[] {
  return [
    ...new Set(
      fields
        .map((field) =>
          field.valueSource === "dictionary" ? field.dictionaryId : null,
        )
        .filter((dictionaryId): dictionaryId is string =>
          Boolean(dictionaryId),
        ),
    ),
  ];
}

function getStoredDictionaryValues(
  fields: readonly DocumentMetadataSchemaField[],
  values: Record<string, MetadataScalar>,
): StoredDictionaryValue[] {
  const entries = fields.flatMap((field) => {
    const value = values[field.key];
    if (
      field.valueSource !== "dictionary" ||
      !field.dictionaryId ||
      typeof value !== "string" ||
      !value
    ) {
      return [];
    }

    return [{ dictionaryId: field.dictionaryId, externalId: value }];
  });
  return [
    ...new Map(
      entries.map((entry) => [
        `${entry.dictionaryId}:${entry.externalId}`,
        entry,
      ]),
    ).values(),
  ];
}

function mergeDictionaryEntries(
  entries: readonly DictionaryLookupEntry[],
  currentEntry: ManualUploadDictionaryEntry,
): DictionaryLookupEntry[] {
  if (entries.some((entry) => entry.externalId === currentEntry.externalId)) {
    return [...entries];
  }

  return [...entries, currentEntry];
}
