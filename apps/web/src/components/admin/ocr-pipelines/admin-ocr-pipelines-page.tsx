"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { GitBranchIcon, PaletteIcon, PlusIcon } from "lucide-react";
import { useTranslations } from "next-intl";
import { useRef, useState } from "react";

import {
  CatalogNotice,
  getCatalogErrorMessage,
} from "@/components/admin/catalog/catalog-shared";
import { ConfidenceColorSettingsSheet } from "@/components/admin/ocr-pipelines/confidence-color-settings-sheet";
import { PipelineBuilderSheet } from "@/components/admin/ocr-pipelines/pipeline-builder-sheet";
import { PipelineDetailPanel } from "@/components/admin/ocr-pipelines/pipeline-detail-panel";
import { PipelineList } from "@/components/admin/ocr-pipelines/pipeline-list";
import { useOcrPipelinesController } from "@/components/admin/ocr-pipelines/use-ocr-pipelines-controller";
import { Button } from "@/components/ui/button";
import { ConfirmActionDialog } from "@/components/ui/confirm-action-dialog";
import {
  DataListActions,
  DataListContent,
  DataListFilters,
  DataListPanel,
  DataListToolbar,
} from "@/components/ui/data-list";
import { DataListChipFilter } from "@/components/ui/data-list-filters";
import { PageBackLink } from "@/components/ui/page-back-link";
import { PageHeader } from "@/components/ui/page-header";
import { PageShell } from "@/components/ui/page-shell";
import { Notice } from "@/components/ui/notice";
import { Sheet } from "@/components/ui/sheet";
import { useCsrfProtectedAction } from "@/hooks/auth/use-csrf-protected-action";
import { confidenceColorsClient } from "@/lib/confidence-colors/api";
import {
  adminConfidenceColorSettingsQueryOptions,
  confidenceColorQueryKeys,
} from "@/lib/confidence-colors/query-options";
import {
  DEFAULT_CONFIDENCE_COLOR_SETTINGS,
  type ConfidenceColorBand,
  type ConfidenceColorSettings,
} from "@/lib/confidence-colors/types";
import { getOcrPipelineRoutingStatus } from "@/lib/ocr-pipelines/diagnostics-view-model";
import {
  getOcrPipelineFilterCount,
  ocrPipelineLifecycleFilters,
} from "@/lib/ocr-pipelines/view-model";

interface ConfidenceColorFormSession {
  id: number;
  settings: ConfidenceColorSettings;
}

interface ConfidenceColorMutationInput {
  bands: ConfidenceColorBand[];
  expectedUpdatedAt: string | null;
}

export function AdminOcrPipelinesPage() {
  const t = useTranslations("AdminOcrPipelines");
  const common = useTranslations("AdminSettings.common");
  const controller = useOcrPipelinesController();
  const queryClient = useQueryClient();
  const runCsrfProtectedAction = useCsrfProtectedAction();
  const [confidenceColorsOpen, setConfidenceColorsOpen] = useState(false);
  const [confidenceColorFormSession, setConfidenceColorFormSession] =
    useState<ConfidenceColorFormSession | null>(null);
  const confidenceColorSessionId = useRef(0);
  const confidenceColorsQuery = useQuery(
    adminConfidenceColorSettingsQueryOptions(),
  );
  const confidenceColorsMutation = useMutation({
    mutationFn: ({ bands, expectedUpdatedAt }: ConfidenceColorMutationInput) =>
      runCsrfProtectedAction((csrfToken) =>
        confidenceColorsClient.updateAdminSettings(bands, expectedUpdatedAt, {
          csrfToken,
        }),
      ),
    onSuccess: (settings) => {
      queryClient.setQueryData(confidenceColorQueryKeys.settings(), settings);
      confidenceColorSessionId.current += 1;
      setConfidenceColorFormSession(null);
      setConfidenceColorsOpen(false);
    },
  });
  const currentDetailPipelineId =
    controller.displayDetail?.id ?? controller.effectiveSelectedPipelineId;
  const editError =
    controller.editError?.pipelineId === currentDetailPipelineId
      ? controller.editError.error
      : null;
  const loadError =
    controller.pipelinesQuery.error ??
    controller.catalogQuery.error ??
    editError;
  const builderError = controller.saveMutation.error
    ? getCatalogErrorMessage(
        controller.saveMutation.error,
        t("builder.errors.saveFailed"),
      )
    : null;
  const selectorCatalogError = controller.selectorCatalogError
    ? getCatalogErrorMessage(
        controller.selectorCatalogError,
        t("builder.errors.selectorCatalogFailed"),
      )
    : null;
  const detailError = controller.detailQuery.error
    ? getCatalogErrorMessage(
        controller.detailQuery.error,
        t("detail.loadFailed"),
      )
    : null;
  const validateError =
    controller.validateMutation.error &&
    controller.validateMutation.variables === currentDetailPipelineId
      ? getCatalogErrorMessage(
          controller.validateMutation.error,
          t("detail.validateFailed"),
        )
      : null;
  const publishError =
    controller.publishMutation.error &&
    controller.publishMutation.variables === currentDetailPipelineId
      ? getCatalogErrorMessage(
          controller.publishMutation.error,
          t("detail.publishFailed"),
        )
      : null;
  const routingStatus = getOcrPipelineRoutingStatus(controller.pipelines);
  const showRoutingStatus =
    !loadError &&
    !controller.pipelinesQuery.isPending &&
    routingStatus !== "ready";

  async function openConfidenceColors() {
    const sessionId = confidenceColorSessionId.current + 1;
    confidenceColorSessionId.current = sessionId;
    confidenceColorsMutation.reset();
    setConfidenceColorFormSession(null);
    setConfidenceColorsOpen(true);

    const result = await confidenceColorsQuery.refetch();
    if (confidenceColorSessionId.current !== sessionId || !result.data) {
      return;
    }
    setConfidenceColorFormSession({
      id: sessionId,
      settings: {
        ...result.data,
        bands: result.data.bands.map((band) => ({ ...band })),
      },
    });
  }

  function closeConfidenceColors() {
    if (confidenceColorsMutation.isPending) {
      return;
    }
    confidenceColorSessionId.current += 1;
    setConfidenceColorFormSession(null);
    setConfidenceColorsOpen(false);
    confidenceColorsMutation.reset();
  }

  return (
    <PageShell
      navigation={<PageBackLink href="/admin">{t("back")}</PageBackLink>}
    >
      <PageHeader
        description={t("description")}
        descriptionClassName="max-w-2xl"
        icon={GitBranchIcon}
        title={t("title")}
      />

      <DataListPanel>
        <DataListToolbar>
          <DataListFilters>
            <DataListChipFilter
              ariaLabel={t("filters.label")}
              onValueChange={controller.handleFilterChange}
              options={ocrPipelineLifecycleFilters.map((item) => ({
                label: t(`filters.${item}`, {
                  count: getOcrPipelineFilterCount(controller.pipelines, item),
                }),
                value: item,
              }))}
              value={controller.filter}
            />
          </DataListFilters>
          <DataListActions>
            <Button
              onClick={() => void openConfidenceColors()}
              size="sm"
              type="button"
              variant="outline"
            >
              <PaletteIcon data-icon="inline-start" />
              {t("actions.confidenceColors")}
            </Button>
            <Button
              onClick={controller.openCreateBuilder}
              size="sm"
              type="button"
            >
              <PlusIcon data-icon="inline-start" />
              {t("actions.create")}
            </Button>
          </DataListActions>
        </DataListToolbar>
        <DataListContent>
          {loadError ? (
            <CatalogNotice
              description={t("errorDescription")}
              title={getCatalogErrorMessage(loadError, t("errorTitle"))}
              tone="danger"
            />
          ) : null}
          {showRoutingStatus ? (
            <Notice
              title={t(`routingStatus.${routingStatus}.title`)}
              description={t(`routingStatus.${routingStatus}.description`)}
            />
          ) : null}

          <div className="grid gap-5 xl:grid-cols-[minmax(0,1.2fr)_minmax(360px,0.8fr)]">
            <PipelineList
              isLoading={controller.pipelinesQuery.isPending}
              onAction={controller.handlePipelineAction}
              pipelines={controller.filteredPipelines}
              selectedPipelineId={controller.effectiveSelectedPipelineId}
            />
            <PipelineDetailPanel
              detail={controller.displayDetail}
              detailError={detailError}
              isLoading={Boolean(
                controller.effectiveSelectedPipelineId &&
                controller.detailQuery.isPending,
              )}
              onEdit={controller.openDetailEditor}
              onPublish={controller.publishSelectedPipeline}
              onValidate={controller.validateSelectedPipeline}
              publishError={publishError}
              publishPending={controller.publishMutation.isPending}
              validateError={validateError}
              validatePending={controller.validateMutation.isPending}
            />
          </div>
        </DataListContent>
      </DataListPanel>

      <Sheet
        onOpenChange={controller.handleBuilderOpenChange}
        open={Boolean(controller.builderTarget)}
      >
        {controller.builderTarget ? (
          <PipelineBuilderSheet
            attributes={controller.activeAttributes}
            blocks={controller.catalogQuery.data?.data.blocks ?? []}
            documentTypes={
              controller.documentTypesQuery.data?.data.documentTypes ?? []
            }
            documentTypeDefinition={
              controller.documentTypeDefinitionQuery.data ?? null
            }
            error={builderError}
            existingPipelineNames={controller.pipelines.map(
              (pipeline) => pipeline.name,
            )}
            isPending={controller.saveMutation.isPending}
            selectorCatalogError={selectorCatalogError}
            selectorCatalogPending={controller.selectorCatalogPending}
            key={
              controller.builderTarget.kind === "create"
                ? "create"
                : `${controller.builderTarget.kind}:${controller.builderTarget.detail.id}`
            }
            onCancel={() => controller.setBuilderTarget(null)}
            onSubmit={controller.submitBuilder}
            target={controller.builderTarget}
          />
        ) : null}
      </Sheet>

      <Sheet
        onOpenChange={(open) => {
          if (!open) closeConfidenceColors();
        }}
        open={confidenceColorsOpen}
      >
        {confidenceColorsOpen ? (
          <ConfidenceColorSettingsSheet
            error={
              !confidenceColorFormSession && confidenceColorsQuery.error
                ? getCatalogErrorMessage(
                    confidenceColorsQuery.error,
                    t("confidenceColors.errors.loadFailed"),
                  )
                : confidenceColorsMutation.error
                  ? getCatalogErrorMessage(
                      confidenceColorsMutation.error,
                      t("confidenceColors.errors.saveFailed"),
                    )
                  : null
            }
            isPending={confidenceColorsMutation.isPending}
            key={confidenceColorFormSession?.id ?? "loading-confidence-colors"}
            onCancel={closeConfidenceColors}
            onSubmit={(bands) => {
              if (!confidenceColorFormSession) return;
              confidenceColorsMutation.mutate({
                bands,
                expectedUpdatedAt:
                  confidenceColorFormSession.settings.updatedAt,
              });
            }}
            saveDisabled={!confidenceColorFormSession}
            settings={
              confidenceColorFormSession?.settings ??
              DEFAULT_CONFIDENCE_COLOR_SETTINGS
            }
          />
        ) : null}
      </Sheet>

      {controller.pendingAction ? (
        <ConfirmActionDialog
          cancelLabel={common("cancel")}
          confirmLabel={t(`confirm.${controller.pendingAction.kind}.confirm`)}
          description={t(
            `confirm.${controller.pendingAction.kind}.description`,
            {
              name: controller.pendingAction.pipelineName,
            },
          )}
          error={
            controller.lifecycleMutation.error ? (
              <CatalogNotice
                title={getCatalogErrorMessage(
                  controller.lifecycleMutation.error,
                  t("actionFailed"),
                )}
                tone="danger"
              />
            ) : null
          }
          isPending={controller.lifecycleMutation.isPending}
          onConfirm={controller.confirmPendingAction}
          onOpenChange={controller.handlePendingActionOpenChange}
          open
          title={t(`confirm.${controller.pendingAction.kind}.title`)}
        />
      ) : null}
    </PageShell>
  );
}
