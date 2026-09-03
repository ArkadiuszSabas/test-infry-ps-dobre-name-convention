import { useTranslations } from "next-intl";

import { isApiError } from "@/lib/api/errors";
import type { InboxDocument } from "@/lib/inbox/types";

type OcrPipelineRunTranslations = ReturnType<typeof useTranslations>;

export function getOcrPipelineRunStartDisabledReason({
  activeRunInProgress,
  canCreateRuns,
  document,
  historyUnavailable,
  historyLoading,
  noPublishedPipelines,
  pipelinesLoading,
  pipelinesUnavailable,
  selectedPipelineMissing,
  t,
}: {
  activeRunInProgress: boolean;
  canCreateRuns: boolean;
  document: InboxDocument;
  historyUnavailable: boolean;
  historyLoading: boolean;
  noPublishedPipelines: boolean;
  pipelinesLoading: boolean;
  pipelinesUnavailable: boolean;
  selectedPipelineMissing: boolean;
  t: OcrPipelineRunTranslations;
}): string | null {
  if (!canCreateRuns) {
    return t("disabled.permission");
  }

  if (document.contentSizeBytes === null) {
    return t("disabled.unknownSize");
  }

  if (pipelinesLoading) {
    return t("disabled.pipelinesLoading");
  }

  if (pipelinesUnavailable) {
    return t("disabled.pipelinesUnavailable");
  }

  if (noPublishedPipelines || selectedPipelineMissing) {
    return t("disabled.noPublishedPipelines");
  }

  if (historyLoading) {
    return t("disabled.historyLoading");
  }

  if (historyUnavailable) {
    return t("disabled.historyUnavailable");
  }

  if (activeRunInProgress) {
    return t("disabled.runInProgress");
  }

  return null;
}

export function getOcrPipelineRunStartErrorMessage(
  error: unknown,
  t: OcrPipelineRunTranslations,
): { description: string; title: string } {
  if (!isApiError(error)) {
    return {
      description: t("errors.genericStartDescription"),
      title: t("errors.genericStartTitle"),
    };
  }

  const translationKey = startErrorTranslationKey(error.code);

  return {
    description: translationKey
      ? t(`errors.${translationKey}.description`)
      : error.message,
    title: translationKey
      ? t(`errors.${translationKey}.title`)
      : t("errors.apiTitle"),
  };
}

function startErrorTranslationKey(code: string): string | null {
  switch (code) {
    case "OCR_PIPELINE_RUN_NO_PUBLISHED_DEFAULT":
      return "noPublishedDefault";
    case "OCR_PIPELINE_RUN_PIPELINE_NOT_RUNNABLE":
      return "pipelineNotRunnable";
    case "OCR_PIPELINE_RUN_DOCUMENT_SIZE_UNKNOWN":
      return "documentSizeUnknown";
    case "OCR_PIPELINE_RUN_LIMIT_EXCEEDED":
      return "limitExceeded";
    case "OCR_PIPELINE_RUN_ALREADY_ACTIVE":
      return "alreadyActive";
    case "OCR_PIPELINE_RUN_DOCUMENT_NOT_FOUND":
      return "documentNotFound";
    default:
      return null;
  }
}
