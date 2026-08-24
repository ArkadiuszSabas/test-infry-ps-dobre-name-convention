"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CopyIcon } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { useState, useSyncExternalStore, type FormEvent } from "react";

import { CatalogFormSection } from "@/components/admin/catalog/catalog-form-section";
import { UnsavedChangesGuard } from "@/components/admin/catalog/unsaved-changes-guard";
import { UnsavedChangesDialog } from "@/components/system-catalogs/unsaved-changes-dialog";
import { useSheetDismissGuard } from "@/components/ui/sheet-dismiss-guard";
import {
  CatalogFormActions,
  CatalogFormSheet,
  CatalogFormSheetContent,
} from "@/components/admin/catalog/catalog-form-sheet";
import { ConnectionTestDialog } from "@/components/admin/connectors/connection-test-dialog";
import { AttributeMappingEditor } from "@/components/admin/connectors/attribute-mapping-editor";
import {
  FieldShell,
  getCatalogErrorMessage,
} from "@/components/admin/catalog/catalog-shared";
import { Button } from "@/components/ui/button";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { ConfirmActionDialog } from "@/components/ui/confirm-action-dialog";
import { FieldGroup } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Notice } from "@/components/ui/notice";
import { PasswordInput } from "@/components/ui/password-input";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Sheet } from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import { DocumentTypeDisplaySelect } from "@/components/system-catalogs/document-type-display-select";
import { useAuthActions } from "@/hooks/auth/auth-actions-context";
import { useRouter } from "@/i18n/navigation";
import { attributesQueryOptions } from "@/lib/admin-settings/query-options";
import { buildApiUrl } from "@/lib/api/client";
import {
  getConnectorConfiguration,
  rotateConnectorApiKey,
  saveConnectorConfiguration,
  testConnectorConfiguration,
  type ConnectorConfigurationTestResult,
} from "@/lib/connector-configurations/api";
import {
  connectorConfigurationLocale,
  getConnectorConfigurationExtension,
  type ConnectorConfigurationTestDiagnosticLabels,
} from "@/lib/connector-configurations/extensions";
import { toAbsoluteConnectorEndpoint } from "@/lib/connector-configurations/intake-endpoint";
import { expectedConnectorConfigurationRevision } from "@/lib/connector-configurations/revision";
import { systemCatalogOptionsQueryOptions } from "@/lib/system-catalogs/query-options";

interface ConnectorConfigurationEditorProps {
  connectorInstanceId: string;
}

function subscribeToBrowserOrigin() {
  return () => {};
}

function getBrowserOrigin(): string {
  return window.location.origin;
}

function getServerBrowserOrigin(): null {
  return null;
}

export function ConnectorConfigurationEditor({
  connectorInstanceId,
}: ConnectorConfigurationEditorProps) {
  const t = useTranslations("AdminConnectors");
  const locale = connectorConfigurationLocale(useLocale());
  const router = useRouter();
  const { csrfToken } = useAuthActions();
  const queryClient = useQueryClient();
  const extension = getConnectorConfigurationExtension(connectorInstanceId);
  const messages = extension?.messages[locale];
  const needsDocumentTypes = Boolean(
    extension?.fields.some((field) => field.kind === "documentType"),
  );
  const needsAttributes = Boolean(
    extension?.fields.some(
      (field) =>
        field.kind === "attribute" || field.kind === "attributeMappings",
    ),
  );
  const query = useQuery({
    queryFn: () => getConnectorConfiguration(connectorInstanceId),
    queryKey: ["connector-configuration", connectorInstanceId],
  });
  const documentTypesQuery = useQuery(
    systemCatalogOptionsQueryOptions("document_type", needsDocumentTypes),
  );
  const attributesQuery = useQuery({
    ...attributesQueryOptions(null),
    enabled: needsAttributes,
  });
  const [values, setValues] = useState<Record<string, string>>({});
  const [draftUpdatedAt, setDraftUpdatedAt] = useState<string | null>();
  const [apiKeyUpdatedAt, setApiKeyUpdatedAt] = useState<string | null>();
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [apiKeyConfirmationOpen, setApiKeyConfirmationOpen] = useState(false);
  const [apiKeyCopied, setApiKeyCopied] = useState(false);
  const [apiKeyCopyError, setApiKeyCopyError] = useState(false);
  const [generatedApiKey, setGeneratedApiKey] = useState<string | null>(null);
  const [connectionTestResult, setConnectionTestResult] = useState<{
    result: ConnectorConfigurationTestResult;
    testId: string;
  } | null>(null);
  const [connectionTestErrorMessage, setConnectionTestErrorMessage] =
    useState<string>();
  const [discardOpen, setDiscardOpen] = useState(false);
  const dismissGuard = useSheetDismissGuard();
  const browserOrigin = useSyncExternalStore(
    subscribeToBrowserOrigin,
    getBrowserOrigin,
    getServerBrowserOrigin,
  );
  const configuration = query.data;
  const intakeEndpoint =
    browserOrigin && extension?.intakeEndpointPath
      ? toAbsoluteConnectorEndpoint(
          buildApiUrl(extension.intakeEndpointPath),
          browserOrigin,
        )
      : null;
  const effectiveValues = Object.fromEntries(
    (configuration?.fieldNames ?? []).map((fieldName) => [
      fieldName,
      values[fieldName] ?? configuration?.values[fieldName] ?? "",
    ]),
  );
  for (const field of extension?.fields ?? []) {
    if (
      field.kind === "attributeMappings" &&
      !effectiveValues[field.name]?.trim()
    ) {
      effectiveValues[field.name] = "[]";
    }
  }
  const documentTypeData = documentTypesQuery.data?.data;
  const activeAttributes =
    attributesQuery.data?.data.attributes.filter(
      (attribute) => attribute.status === "active",
    ) ?? [];
  const save = useMutation({
    mutationFn: (submittedValues: Record<string, string>) =>
      saveConnectorConfiguration(
        connectorInstanceId,
        {
          expectedUpdatedAt: expectedConnectorConfigurationRevision(
            draftUpdatedAt,
            configuration?.updatedAt ?? null,
          ),
          values: submittedValues,
        },
        csrfToken,
      ),
    onSuccess: (data) => {
      setValues(data.values);
      setDraftUpdatedAt(data.updatedAt);
      queryClient.setQueryData(
        ["connector-configuration", connectorInstanceId],
        data,
      );
    },
  });
  const rotateKey = useMutation({
    mutationFn: (expectedUpdatedAt: string | null) =>
      rotateConnectorApiKey(connectorInstanceId, expectedUpdatedAt, csrfToken),
    onSuccess: (data) => {
      setApiKeyConfirmationOpen(false);
      setApiKeyCopied(false);
      setApiKeyCopyError(false);
      setGeneratedApiKey(data.generatedApiKey);
      setApiKeyUpdatedAt(data.updatedAt);
      setDraftUpdatedAt(data.updatedAt);
      queryClient.setQueryData(
        ["connector-configuration", connectorInstanceId],
        { ...data, generatedApiKey: null },
      );
    },
  });
  const connectionTest = useMutation({
    mutationFn: ({
      submittedValues,
      testId,
    }: {
      submittedValues: Record<string, string>;
      testId: string;
    }) =>
      testConnectorConfiguration(
        connectorInstanceId,
        testId,
        submittedValues,
        csrfToken,
      ),
    onSuccess: (result, variables) =>
      setConnectionTestResult({ result, testId: variables.testId }),
  });
  const isPending =
    save.isPending || rotateKey.isPending || connectionTest.isPending;
  const isDirty = Boolean(
    configuration &&
    configuration.fieldNames.some(
      (fieldName) =>
        effectiveValues[fieldName] !== (configuration.values[fieldName] ?? ""),
    ),
  );
  const connectionTestSectionMessages =
    connectionTestResult && messages
      ? Object.values(messages.sections).find(
          (section) => section.connectionTestId === connectionTestResult.testId,
        )
      : undefined;

  const closeEditor = () => {
    if (!isPending) router.push("/admin/connectors");
  };

  const requestCloseEditor = () => {
    if (isPending) return;
    if (dismissGuard?.isDiscardingRef.current) {
      closeEditor();
      return;
    }
    if (isDirty) {
      setDiscardOpen(true);
      return;
    }
    closeEditor();
  };

  const copyGeneratedApiKey = async () => {
    if (!generatedApiKey) return;
    try {
      await navigator.clipboard.writeText(generatedApiKey);
      setApiKeyCopied(true);
      setApiKeyCopyError(false);
    } catch {
      setApiKeyCopied(false);
      setApiKeyCopyError(true);
    }
  };

  const closeGeneratedApiKey = () => {
    setGeneratedApiKey(null);
    setApiKeyCopied(false);
    setApiKeyCopyError(false);
  };

  const updateValue = (fieldName: string, value: string) => {
    setConnectionTestResult(null);
    connectionTest.reset();
    setDraftUpdatedAt((current) =>
      current === undefined ? (configuration?.updatedAt ?? null) : current,
    );
    setValues((current) => ({
      ...effectiveValues,
      ...current,
      [fieldName]: value,
    }));
    setFieldErrors((current) => {
      const next = { ...current };
      delete next[fieldName];
      return next;
    });
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!extension) return;

    const errors = extension.validate(effectiveValues, locale);
    setFieldErrors(errors);
    if (Object.keys(errors).length > 0) return;

    save.mutate(effectiveValues);
  };

  const footerError = Object.keys(fieldErrors).length
    ? t("fixFields")
    : save.isError
      ? getCatalogErrorMessage(save.error, t("saveError"))
      : connectionTest.isError
        ? getCatalogErrorMessage(
            connectionTest.error,
            connectionTestErrorMessage ?? t("saveError"),
          )
        : undefined;

  return (
    <>
      <Sheet
        onOpenChange={(open) => {
          if (!open) requestCloseEditor();
        }}
        open
      >
        <CatalogFormSheetContent size="wide">
          <CatalogFormSheet
            description={messages?.formDescription ?? connectorInstanceId}
            footer={
              <CatalogFormActions
                cancelLabel={t("cancel")}
                error={footerError}
                isPending={isPending}
                onCancel={requestCloseEditor}
                saveDisabled={!configuration || !extension}
                saveLabel={t("save")}
                savingLabel={t("saving")}
              />
            }
            onSubmit={handleSubmit}
            title={messages?.formTitle ?? t("title")}
          >
            {query.isPending ? <ConnectorConfigurationSkeleton /> : null}

            {query.isError ? (
              <Notice title={t("loadConfigurationError")} tone="danger" />
            ) : null}

            {!extension ? (
              <Notice title={t("unsupportedConfiguration")} tone="danger" />
            ) : null}

            {configuration && extension && messages ? (
              <>
                {extension.sections.map((sectionName) => {
                  const sectionMessages = messages.sections[sectionName];
                  if (sectionName === "authentication") {
                    return (
                      <CatalogFormSection
                        description={sectionMessages.description}
                        key={sectionName}
                        title={sectionMessages.title}
                      >
                        <div className="flex flex-col gap-4">
                          {intakeEndpoint ? (
                            <FieldShell
                              description={messages.intakeEndpointDescription}
                              htmlFor="connector-configuration-intake-endpoint"
                              label={messages.intakeEndpointLabel}
                            >
                              <Input
                                id="connector-configuration-intake-endpoint"
                                readOnly
                                value={intakeEndpoint}
                              />
                            </FieldShell>
                          ) : null}
                          <div className="flex flex-col gap-4 rounded-lg border bg-muted/20 p-4 sm:flex-row sm:items-center sm:justify-between">
                            <div className="min-w-0">
                              <p className="font-medium">
                                {configuration.apiKeyConfigured
                                  ? messages.apiKeyConfigured
                                  : messages.apiKeyNotConfigured}
                              </p>
                              <p className="mt-1 text-sm text-muted-foreground">
                                {configuration.apiKeyConfigured
                                  ? messages.apiKeyConfiguredDescription
                                  : messages.apiKeyNotConfiguredDescription}
                              </p>
                            </div>
                            <Button
                              className="shrink-0"
                              disabled={isPending}
                              onClick={() => {
                                rotateKey.reset();
                                setApiKeyUpdatedAt(configuration.updatedAt);
                                setApiKeyConfirmationOpen(true);
                              }}
                              type="button"
                              variant="outline"
                            >
                              {messages.generateApiKey}
                            </Button>
                          </div>
                        </div>
                      </CatalogFormSection>
                    );
                  }

                  const sectionFields = extension.fields.filter(
                    (field) => field.section === sectionName,
                  );
                  const connectionTestId = sectionMessages.connectionTestId;
                  if (sectionFields.length === 0) return null;

                  return (
                    <CatalogFormSection
                      description={sectionMessages.description}
                      key={sectionName}
                      title={sectionMessages.title}
                    >
                      <FieldGroup>
                        {sectionMessages.notice ? (
                          <Notice title={sectionMessages.notice} />
                        ) : null}
                        {sectionFields.map((field) => {
                          const fieldMessages = messages.fields[field.name];
                          if (!fieldMessages) return null;

                          const fieldId = `connector-configuration-${field.name}`;

                          return (
                            <FieldShell
                              description={fieldMessages.description}
                              error={fieldErrors[field.name]}
                              htmlFor={fieldId}
                              key={field.name}
                              label={fieldMessages.label}
                              required
                              requiredLabel={t("required")}
                            >
                              {field.kind === "documentType" ? (
                                <DocumentTypeDisplaySelect
                                  ariaLabel={fieldMessages.label}
                                  definition={documentTypeData?.definition}
                                  disabled={
                                    isPending || documentTypesQuery.isPending
                                  }
                                  emptyMessage={t("noDocumentTypes")}
                                  id={fieldId}
                                  invalid={Boolean(fieldErrors[field.name])}
                                  onValueChange={(value) =>
                                    updateValue(field.name, value)
                                  }
                                  options={documentTypeData?.options ?? []}
                                  placeholder={fieldMessages.placeholder}
                                  searchPlaceholder={t("searchDocumentTypes")}
                                  triggerClassName="min-w-0 flex-1"
                                  value={effectiveValues[field.name] ?? ""}
                                />
                              ) : field.kind === "attribute" ? (
                                <Select
                                  disabled={
                                    isPending || attributesQuery.isPending
                                  }
                                  onValueChange={(value) =>
                                    updateValue(field.name, value)
                                  }
                                  value={effectiveValues[field.name] ?? ""}
                                >
                                  <SelectTrigger
                                    aria-invalid={Boolean(
                                      fieldErrors[field.name],
                                    )}
                                    aria-label={fieldMessages.label}
                                    className="w-full"
                                    id={fieldId}
                                  >
                                    <SelectValue
                                      placeholder={fieldMessages.placeholder}
                                    />
                                  </SelectTrigger>
                                  <SelectContent>
                                    <SelectGroup>
                                      {activeAttributes.map((attribute) => (
                                        <SelectItem
                                          key={attribute.id}
                                          value={attribute.id}
                                        >
                                          {attribute.name}
                                        </SelectItem>
                                      ))}
                                    </SelectGroup>
                                  </SelectContent>
                                </Select>
                              ) : field.kind === "attributeMappings" ? (
                                <AttributeMappingEditor
                                  attributes={activeAttributes}
                                  disabled={
                                    isPending || attributesQuery.isPending
                                  }
                                  id={fieldId}
                                  invalid={Boolean(fieldErrors[field.name])}
                                  messages={fieldMessages}
                                  onValueChange={(value) =>
                                    updateValue(field.name, value)
                                  }
                                  value={effectiveValues[field.name] ?? "[]"}
                                />
                              ) : (
                                <Input
                                  aria-invalid={Boolean(
                                    fieldErrors[field.name],
                                  )}
                                  disabled={isPending}
                                  id={fieldId}
                                  inputMode={field.inputMode}
                                  onChange={(event) =>
                                    updateValue(field.name, event.target.value)
                                  }
                                  placeholder={fieldMessages.placeholder}
                                  type={field.inputType ?? "text"}
                                  value={effectiveValues[field.name] ?? ""}
                                />
                              )}
                            </FieldShell>
                          );
                        })}
                        {sectionMessages.actionLabel && connectionTestId ? (
                          <div className="flex flex-col gap-3">
                            <Button
                              className="self-start"
                              disabled={isPending}
                              onClick={() => {
                                const errors = extension.validate(
                                  effectiveValues,
                                  locale,
                                );
                                setFieldErrors(errors);
                                if (Object.keys(errors).length === 0) {
                                  setConnectionTestResult(null);
                                  setConnectionTestErrorMessage(
                                    sectionMessages.connectionTestError,
                                  );
                                  connectionTest.mutate({
                                    submittedValues: effectiveValues,
                                    testId: connectionTestId,
                                  });
                                }
                              }}
                              type="button"
                              variant="outline"
                            >
                              {sectionMessages.actionLabel}
                            </Button>
                            {connectionTestResult?.testId ===
                              connectionTestId &&
                            sectionMessages.connectionTestResults &&
                            !sectionMessages.connectionTestDialog ? (
                              <Notice
                                description={formatConnectionTestDiagnostics(
                                  connectionTestResult.result,
                                  sectionMessages.connectionTestDiagnosticLabels,
                                )}
                                title={
                                  sectionMessages.connectionTestResults[
                                    connectionTestResult.result.status
                                  ] ??
                                  sectionMessages.connectionTestError ??
                                  messages.formTitle
                                }
                                tone={
                                  connectionTestResult.result.status ===
                                  "success"
                                    ? "default"
                                    : "danger"
                                }
                              />
                            ) : null}
                          </div>
                        ) : null}
                      </FieldGroup>
                    </CatalogFormSection>
                  );
                })}
              </>
            ) : null}
          </CatalogFormSheet>
          {configuration && messages ? (
            <ConfirmActionDialog
              cancelLabel={t("cancel")}
              confirmLabel={
                rotateKey.isPending
                  ? messages.generatingApiKey
                  : messages.confirmApiKeyRotation
              }
              confirmVariant={
                configuration.apiKeyConfigured ? "destructive" : "default"
              }
              description={
                configuration.apiKeyConfigured
                  ? messages.confirmApiKeyRotationDescription
                  : messages.confirmApiKeyGenerationDescription
              }
              error={
                rotateKey.isError ? (
                  <Notice
                    title={getCatalogErrorMessage(
                      rotateKey.error,
                      messages.apiKeyRotationError,
                    )}
                    tone="danger"
                  />
                ) : undefined
              }
              isPending={rotateKey.isPending}
              onConfirm={() =>
                rotateKey.mutate(
                  expectedConnectorConfigurationRevision(
                    apiKeyUpdatedAt,
                    configuration.updatedAt,
                  ),
                )
              }
              onOpenChange={(open) => {
                if (!rotateKey.isPending) setApiKeyConfirmationOpen(open);
              }}
              open={apiKeyConfirmationOpen}
              title={
                configuration.apiKeyConfigured
                  ? messages.confirmApiKeyRotationTitle
                  : messages.confirmApiKeyGenerationTitle
              }
            />
          ) : null}
          <AlertDialog
            onOpenChange={(open) => {
              if (!open) closeGeneratedApiKey();
            }}
            open={generatedApiKey !== null}
          >
            <AlertDialogContent size="sm">
              <AlertDialogHeader>
                <AlertDialogTitle>{messages?.generatedApiKey}</AlertDialogTitle>
                <AlertDialogDescription>
                  {messages?.copyApiKey}
                </AlertDialogDescription>
              </AlertDialogHeader>
              {generatedApiKey && messages ? (
                <PasswordInput
                  aria-label={messages.generatedApiKey}
                  className="font-mono"
                  hideLabel={messages.hideApiKey}
                  readOnly
                  showLabel={messages.showApiKey}
                  value={generatedApiKey}
                />
              ) : null}
              {apiKeyCopyError && messages ? (
                <Notice title={messages.apiKeyCopyError} tone="danger" />
              ) : null}
              <AlertDialogFooter>
                <Button
                  onClick={copyGeneratedApiKey}
                  type="button"
                  variant="outline"
                >
                  <CopyIcon data-icon="inline-start" />
                  {apiKeyCopied
                    ? messages?.apiKeyCopied
                    : messages?.copyApiKeyAction}
                </Button>
                <AlertDialogAction onClick={closeGeneratedApiKey}>
                  {messages?.closeGeneratedApiKey}
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
          {connectionTestResult &&
          connectionTestSectionMessages?.connectionTestDialog &&
          connectionTestSectionMessages.connectionTestResults ? (
            <ConnectionTestDialog
              messages={connectionTestSectionMessages.connectionTestDialog}
              onClose={() => setConnectionTestResult(null)}
              open
              result={connectionTestResult.result}
              summary={
                connectionTestSectionMessages.connectionTestResults[
                  connectionTestResult.result.status
                ] ??
                connectionTestSectionMessages.connectionTestError ??
                messages?.formTitle ??
                ""
              }
            />
          ) : null}
        </CatalogFormSheetContent>

        <UnsavedChangesGuard isDirty={isDirty} />
      </Sheet>
      <UnsavedChangesDialog
        onDiscard={() => {
          setDiscardOpen(false);
          closeEditor();
        }}
        onOpenChange={setDiscardOpen}
        open={discardOpen}
      />
    </>
  );
}

function formatConnectionTestDiagnostics(
  result: ConnectorConfigurationTestResult,
  labels: ConnectorConfigurationTestDiagnosticLabels | undefined,
): string | undefined {
  if (!labels) return undefined;
  const values = [
    result.operation ? `${labels.operation}: ${result.operation}` : null,
    result.failureCode ? `${labels.failureCode}: ${result.failureCode}` : null,
    result.httpStatusCode
      ? `${labels.httpStatusCode}: ${result.httpStatusCode}`
      : null,
  ].filter((value): value is string => value !== null);
  return values.length > 0 ? values.join(" · ") : undefined;
}

function ConnectorConfigurationSkeleton() {
  return (
    <div className="grid gap-4">
      <Skeleton className="h-40 w-full" />
      <Skeleton className="h-40 w-full" />
      <Skeleton className="h-28 w-full" />
    </div>
  );
}
