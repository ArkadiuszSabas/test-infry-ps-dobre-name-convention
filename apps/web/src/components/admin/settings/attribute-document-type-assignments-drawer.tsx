"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useCsrfProtectedAction } from "@/hooks/auth/use-csrf-protected-action";
import { isApiError } from "@/lib/api/errors";
import { adminCatalogClient } from "@/lib/admin-settings/api";
import { adminCatalogQueryKeys } from "@/lib/admin-settings/query-options";
import type { AttributeDefinition } from "@/lib/admin-settings/types";

export function AttributeDocumentTypeAssignmentsDrawer({
  attribute,
  onRequestClose,
  onSaved,
  onDirtyChange,
}: {
  attribute: AttributeDefinition;
  onRequestClose: () => void;
  onSaved: () => void;
  onDirtyChange: (dirty: boolean) => void;
}) {
  const t = useTranslations("AdminSettings.attributes.assignments");
  const common = useTranslations("AdminSettings.common");
  const queryClient = useQueryClient();
  const csrf = useCsrfProtectedAction();
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState<"all" | "assigned" | "unassigned">(
    "all",
  );
  const [draft, setDraft] = useState<
    Record<string, "required" | "optional" | "unassigned">
  >({});
  const [missingActions, setMissingActions] = useState<
    Record<string, "block_approval" | "require_review">
  >({});
  const [contextResolver, setContextResolver] = useState<
    Record<string, boolean>
  >({});
  const query = useQuery({
    queryKey: [
      ...adminCatalogQueryKeys.attributes(),
      attribute.id,
      "assignments",
    ],
    queryFn: () => adminCatalogClient.getAttributeAssignments(attribute.id),
    retry: false,
  });
  const isMetadata = query.data?.data.attribute.isMetadata ?? false;
  const dirtyCount = new Set([
    ...Object.keys(draft),
    ...Object.keys(missingActions),
    ...(isMetadata ? Object.keys(contextResolver) : []),
  ]).size;
  useEffect(() => {
    onDirtyChange(dirtyCount > 0);
  }, [dirtyCount, onDirtyChange]);
  const rows = useMemo(
    () =>
      (query.data?.data.assignments ?? []).filter(
        (row) =>
          (!search ||
            `${row.documentType.name} ${row.documentType.externalId ?? ""}`
              .toLowerCase()
              .includes(search.toLowerCase())) &&
          (filter === "all" ||
            (filter === "assigned"
              ? (draft[row.documentType.id] ?? row.state) !== "unassigned"
              : (draft[row.documentType.id] ?? row.state) === "unassigned")),
      ),
    [draft, filter, query.data, search],
  );
  const save = useMutation({
    mutationFn: () =>
      csrf((csrfToken) =>
        adminCatalogClient.saveAttributeAssignments(
          attribute.id,
          query.data?.meta.version ?? "",
          (query.data?.data.assignments ?? [])
            .map((row) => {
              const state = draft[row.documentType.id] ?? row.state;
              const required = state === "required";
              return {
                documentTypeId: row.documentType.id,
                required,
                includeMetadataInContextResolver: isMetadata
                  ? (contextResolver[row.documentType.id] ??
                    row.includeMetadataInContextResolver)
                  : false,
                missingRequiredAction: required
                  ? (missingActions[row.documentType.id] ??
                    row.missingRequiredAction ??
                    "block_approval")
                  : null,
              };
            })
            .filter(
              (item, index) =>
                (draft[
                  query.data?.data.assignments[index]?.documentType.id ?? ""
                ] ?? query.data?.data.assignments[index]?.state) !==
                "unassigned",
            ),
          { csrfToken },
        ),
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: [
          ...adminCatalogQueryKeys.attributes(),
          attribute.id,
          "assignments",
        ],
      });
      queryClient.invalidateQueries({
        queryKey: adminCatalogQueryKeys.attributeRequirements(),
      });
      onSaved();
    },
  });
  const isConflict =
    isApiError(save.error) &&
    save.error.code === "ATTRIBUTE_ASSIGNMENT_VERSION_CONFLICT";
  const loadErrorMessage = isApiError(query.error)
    ? query.error.status === 403
      ? t("forbidden")
      : query.error.status === 404
        ? t("notFound")
        : t("error")
    : t("error");
  const saveErrorMessage = isApiError(save.error)
    ? save.error.code === "ATTRIBUTE_REQUIREMENT_VALIDATION_ERROR"
      ? t("validation")
      : save.error.message
    : t("saveError");
  function reloadCurrentState() {
    setDraft({});
    setMissingActions({});
    setContextResolver({});
    save.reset();
    void query.refetch();
  }
  return (
    <SheetContent className="w-full gap-0 overflow-hidden p-0 sm:!max-w-3xl">
      <SheetHeader className="border-b pr-12">
        <SheetTitle>{t("title", { name: attribute.name })}</SheetTitle>
        {dirtyCount > 0 ? (
          <p className="text-sm text-muted-foreground">
            {t("unsaved", { count: dirtyCount })}
          </p>
        ) : null}
      </SheetHeader>
      <div className="flex flex-col gap-3 border-b p-4">
        <Input
          aria-label={t("search")}
          disabled={save.isPending}
          onChange={(event) => setSearch(event.target.value)}
          placeholder={t("search")}
          value={search}
        />
        <div className="flex flex-wrap gap-2">
          <Button
            disabled={save.isPending}
            onClick={() => setFilter("all")}
            size="sm"
            variant={filter === "all" ? "default" : "outline"}
          >
            {t("all")}
          </Button>
          <Button
            disabled={save.isPending}
            onClick={() => setFilter("assigned")}
            size="sm"
            variant={filter === "assigned" ? "default" : "outline"}
          >
            {t("assigned")}
          </Button>
          <Button
            disabled={save.isPending}
            onClick={() => setFilter("unassigned")}
            size="sm"
            variant={filter === "unassigned" ? "default" : "outline"}
          >
            {t("unassigned")}
          </Button>
        </div>
      </div>
      {query.data ? (
        <p className="border-b px-4 py-3 text-sm text-muted-foreground">
          {t("summary", {
            assigned: query.data.meta.assignedCount,
            total: query.data.meta.totalCount,
            unassigned: query.data.meta.unassignedCount,
          })}
        </p>
      ) : null}
      {query.isPending ? (
        <p className="p-4">{t("loading")}</p>
      ) : query.isError ? (
        <p className="p-4" role="alert">
          {loadErrorMessage}
        </p>
      ) : (
        <div className="min-h-0 flex-1 space-y-3 overflow-y-auto p-4">
          {rows.length === 0 ? (
            <p className="text-sm text-muted-foreground">{t("empty")}</p>
          ) : null}
          {rows.map((row) => (
            <div
              aria-label={row.documentType.name}
              className="grid grid-cols-1 gap-3 rounded-lg border p-4 sm:grid-cols-[minmax(0,1fr)_11rem]"
              key={row.documentType.id}
              role="group"
            >
              <div className="min-w-0">
                <p className="wrap-break-word font-medium">
                  {row.documentType.name}
                </p>
                {row.documentType.externalId ? (
                  <p className="wrap-break-word text-xs text-muted-foreground">
                    {row.documentType.externalId}
                  </p>
                ) : null}
                <span className="mt-1 inline-block text-xs text-muted-foreground">
                  {common(`status.${row.documentType.status}`)}
                </span>
              </div>
              <div className="flex min-w-0 flex-col gap-2">
                <Select
                  disabled={save.isPending}
                  value={draft[row.documentType.id] ?? row.state}
                  onValueChange={(value) =>
                    setDraft((current) => {
                      if (value === row.state) {
                        const next = { ...current };
                        delete next[row.documentType.id];
                        return next;
                      }
                      return {
                        ...current,
                        [row.documentType.id]: value as
                          | "required"
                          | "optional"
                          | "unassigned",
                      };
                    })
                  }
                >
                  <SelectTrigger
                    aria-label={row.documentType.name}
                    className="w-full"
                  >
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="required">{t("required")}</SelectItem>
                    <SelectItem value="optional">{t("optional")}</SelectItem>
                    <SelectItem value="unassigned">
                      {t("unassigned")}
                    </SelectItem>
                  </SelectContent>
                </Select>
                {(draft[row.documentType.id] ?? row.state) === "required" ? (
                  <Select
                    disabled={save.isPending}
                    value={
                      missingActions[row.documentType.id] ??
                      row.missingRequiredAction ??
                      "block_approval"
                    }
                    onValueChange={(value) =>
                      setMissingActions((current) => {
                        const original =
                          row.missingRequiredAction ?? "block_approval";
                        if (value === original) {
                          const next = { ...current };
                          delete next[row.documentType.id];
                          return next;
                        }
                        return {
                          ...current,
                          [row.documentType.id]: value as
                            | "block_approval"
                            | "require_review",
                        };
                      })
                    }
                  >
                    <SelectTrigger
                      aria-label={t("missingAction")}
                      className="w-full"
                    >
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="block_approval">
                        {t("blockApproval")}
                      </SelectItem>
                      <SelectItem value="require_review">
                        {t("requireReview")}
                      </SelectItem>
                    </SelectContent>
                  </Select>
                ) : null}
                {isMetadata &&
                (draft[row.documentType.id] ?? row.state) !== "unassigned" ? (
                  <label className="flex items-center gap-2 text-sm">
                    <input
                      checked={
                        contextResolver[row.documentType.id] ??
                        row.includeMetadataInContextResolver
                      }
                      disabled={save.isPending}
                      onChange={(event) =>
                        setContextResolver((current) => {
                          if (
                            event.target.checked ===
                            row.includeMetadataInContextResolver
                          ) {
                            const next = { ...current };
                            delete next[row.documentType.id];
                            return next;
                          }
                          return {
                            ...current,
                            [row.documentType.id]: event.target.checked,
                          };
                        })
                      }
                      type="checkbox"
                    />
                    {t("contextResolver")}
                  </label>
                ) : null}
              </div>
            </div>
          ))}
        </div>
      )}
      {save.isError ? (
        <div
          className="mx-4 rounded-md border border-destructive/30 p-3 text-sm"
          role="alert"
        >
          <p>{isConflict ? t("conflict") : saveErrorMessage}</p>
          {isConflict ? (
            <Button onClick={reloadCurrentState} size="sm" variant="outline">
              {t("reload")}
            </Button>
          ) : null}
        </div>
      ) : null}
      <div className="mt-auto flex justify-end gap-2 border-t p-4">
        <Button
          disabled={save.isPending}
          onClick={onRequestClose}
          variant="outline"
        >
          {t("cancel")}
        </Button>
        <Button
          disabled={save.isPending || query.isPending || dirtyCount === 0}
          onClick={() => save.mutate()}
        >
          {t("save")}
        </Button>
      </div>
    </SheetContent>
  );
}
