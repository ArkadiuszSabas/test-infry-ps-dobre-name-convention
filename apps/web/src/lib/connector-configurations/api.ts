import { apiFetch } from "@/lib/api/client";

export interface ConnectorInstanceDto {
  connector_instance_id: string;
  module_id: string | null;
  status: "degraded" | "disabled" | "enabled" | "unconfigured";
  safe_metadata: { label: string; description: string | null };
}

interface CapabilitiesEnvelope {
  data: { connector_instances: ConnectorInstanceDto[] };
}

export interface ConnectorConfiguration {
  connectorInstanceId: string;
  fieldNames: string[];
  values: Record<string, string>;
  apiKeyConfigured: boolean;
  generatedApiKey: string | null;
  updatedAt: string | null;
}

export type ConnectorConfigurationTestStatus =
  | "authentication"
  | "authorization"
  | "column_not_found"
  | "configuration"
  | "folder_not_found"
  | "library_not_found"
  | "secret_unavailable"
  | "site_not_found"
  | "success"
  | "timeout"
  | "unavailable";

export interface ConnectorConfigurationTestDiagnostic {
  code: string;
  details: Record<string, string>;
  status: "error" | "info" | "success";
}

export interface ConnectorConfigurationTestResult {
  diagnostics: ConnectorConfigurationTestDiagnostic[];
  failureCode: string | null;
  httpStatusCode: number | null;
  operation: string | null;
  status: ConnectorConfigurationTestStatus;
}

interface ConnectorConfigurationEnvelope {
  data: {
    connector_instance_id: string;
    field_names: string[];
    values: Record<string, string>;
    api_key_configured: boolean;
    generated_api_key: string | null;
    updated_at: string | null;
  };
}

interface ConnectorConfigurationTestEnvelope {
  data: {
    diagnostics: {
      code: string;
      details: Record<string, string>;
      status: "error" | "info" | "success";
    }[];
    failure_code: string | null;
    http_status_code: number | null;
    operation: string | null;
    status: ConnectorConfigurationTestStatus;
  };
}

export async function listConfigurableConnectorInstances(): Promise<
  ConnectorInstanceDto[]
> {
  const response = await apiFetch<CapabilitiesEnvelope>("/capabilities");
  return response.data.connector_instances.filter(
    (item) => item.module_id !== null,
  );
}

export async function getConnectorConfiguration(
  connectorInstanceId: string,
): Promise<ConnectorConfiguration> {
  return mapConfiguration(
    await apiFetch<ConnectorConfigurationEnvelope>(
      `/connector-configurations/${encodeURIComponent(connectorInstanceId)}`,
    ),
  );
}

export async function saveConnectorConfiguration(
  connectorInstanceId: string,
  input: {
    values: Record<string, string>;
    expectedUpdatedAt: string | null;
  },
  csrfToken: string | null,
): Promise<ConnectorConfiguration> {
  return mapConfiguration(
    await apiFetch<ConnectorConfigurationEnvelope>(
      `/connector-configurations/${encodeURIComponent(connectorInstanceId)}`,
      {
        csrfToken,
        json: {
          expected_updated_at: input.expectedUpdatedAt,
          values: input.values,
        },
        method: "PUT",
      },
    ),
  );
}

export async function rotateConnectorApiKey(
  connectorInstanceId: string,
  expectedUpdatedAt: string | null,
  csrfToken: string | null,
): Promise<ConnectorConfiguration> {
  return mapConfiguration(
    await apiFetch<ConnectorConfigurationEnvelope>(
      `/connector-configurations/${encodeURIComponent(connectorInstanceId)}/api-key`,
      {
        csrfToken,
        json: { expected_updated_at: expectedUpdatedAt },
        method: "POST",
      },
    ),
  );
}

export async function testConnectorConfiguration(
  connectorInstanceId: string,
  testId: string,
  values: Record<string, string>,
  csrfToken: string | null,
): Promise<ConnectorConfigurationTestResult> {
  const response = await apiFetch<ConnectorConfigurationTestEnvelope>(
    `/connector-configurations/${encodeURIComponent(connectorInstanceId)}/connection-test`,
    {
      csrfToken,
      json: { test_id: testId, values },
      method: "POST",
    },
  );
  return {
    diagnostics: response.data.diagnostics.map((diagnostic) => ({
      code: diagnostic.code,
      details: diagnostic.details,
      status: diagnostic.status,
    })),
    failureCode: response.data.failure_code,
    httpStatusCode: response.data.http_status_code,
    operation: response.data.operation,
    status: response.data.status,
  };
}

function mapConfiguration(
  response: ConnectorConfigurationEnvelope,
): ConnectorConfiguration {
  return {
    apiKeyConfigured: response.data.api_key_configured,
    generatedApiKey: response.data.generated_api_key,
    updatedAt: response.data.updated_at,
    connectorInstanceId: response.data.connector_instance_id,
    fieldNames: response.data.field_names,
    values: response.data.values,
  };
}
