# Observability Module

Creates the environment Log Analytics Workspace, workspace-based Application Insights
component, and Azure Monitor Private Link Scope used by backend runtime observability.

The workspace is environment-local. Retention is selected by the root module:
shorter for `dev`, longer for `prd`. Application Insights is linked to that workspace,
uses private-only ingestion/query, and is added to the same AMPLS as Log Analytics.

The module outputs the Application Insights resource ID, name, and connection string.
The connection string is non-secret runtime configuration consumed by the API, LLM Magic,
and Worker Container Apps. The AzureRM provider marks this field sensitive, so the module
uses `nonsensitive()` to declassify it intentionally; do not hardcode it in application code
or environment files.

## Navigation

- Up: [Terraform Design](../../../docs/terraform-design.md)
- Up: [Infrastructure Documentation](../../../docs/INDEX.md)
