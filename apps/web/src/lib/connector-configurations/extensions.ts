import { connectorConfigurationExtensions } from "@docmind/connector-configuration-registry";

import type { ConnectorConfigurationTestStatus } from "./api";

export interface ConnectorConfigurationFieldDefinition {
  inputMode?: "numeric";
  inputType?: "text" | "url";
  kind: "attribute" | "attributeMappings" | "documentType" | "input";
  name: string;
  section: string;
}

export interface ConnectorConfigurationFieldMessages {
  addLabel?: string;
  attributePlaceholder?: string;
  columnLabel?: string;
  description: string;
  label: string;
  placeholder: string;
  removeLabel?: string;
}

export interface ConnectorConfigurationTestDiagnosticLabels {
  failureCode: string;
  httpStatusCode: string;
  operation: string;
}

export interface ConnectorConfigurationTestDialogMessages {
  closeLabel: string;
  detailLabels: Record<string, string>;
  outcomeLabels: Record<"error" | "info" | "success", string>;
  stepLabels: Record<string, string>;
  title: string;
}

export interface ConnectorConfigurationSectionMessages {
  actionLabel?: string;
  connectionTestDiagnosticLabels?: ConnectorConfigurationTestDiagnosticLabels;
  connectionTestDialog?: ConnectorConfigurationTestDialogMessages;
  connectionTestError?: string;
  connectionTestId?: string;
  connectionTestResults?: Partial<
    Record<ConnectorConfigurationTestStatus, string>
  >;
  description: string;
  notice?: string;
  title: string;
}

export interface ConnectorConfigurationMessages {
  apiKeyConfigured: string;
  apiKeyConfiguredDescription: string;
  apiKeyCopied: string;
  apiKeyCopyError: string;
  apiKeyNotConfigured: string;
  apiKeyNotConfiguredDescription: string;
  apiKeyRotationError: string;
  cardDescription: string;
  cardTitle: string;
  closeGeneratedApiKey: string;
  confirmApiKeyGenerationDescription: string;
  confirmApiKeyGenerationTitle: string;
  confirmApiKeyRotation: string;
  confirmApiKeyRotationDescription: string;
  confirmApiKeyRotationTitle: string;
  copyApiKey: string;
  copyApiKeyAction: string;
  fields: Record<string, ConnectorConfigurationFieldMessages>;
  formDescription: string;
  formTitle: string;
  generateApiKey: string;
  generatingApiKey: string;
  generatedApiKey: string;
  hideApiKey: string;
  intakeEndpointDescription: string;
  intakeEndpointLabel: string;
  sections: Record<string, ConnectorConfigurationSectionMessages>;
  showApiKey: string;
}

export interface ConnectorConfigurationExtension {
  connectorInstanceId: string;
  fields: readonly ConnectorConfigurationFieldDefinition[];
  intakeEndpointPath?: string;
  messages: Record<"en" | "pl", ConnectorConfigurationMessages>;
  sections: readonly string[];
  validate(
    values: Record<string, string>,
    locale: "en" | "pl",
  ): Record<string, string>;
}

const extensions: readonly ConnectorConfigurationExtension[] =
  connectorConfigurationExtensions;

export function getConnectorConfigurationExtension(
  connectorInstanceId: string,
): ConnectorConfigurationExtension | null {
  return (
    extensions.find(
      (extension) => extension.connectorInstanceId === connectorInstanceId,
    ) ?? null
  );
}

export function connectorConfigurationLocale(locale: string): "en" | "pl" {
  return locale === "pl" ? "pl" : "en";
}
