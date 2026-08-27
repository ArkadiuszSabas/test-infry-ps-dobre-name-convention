output "log_analytics_workspace_id" {
  description = "Log Analytics Workspace resource ID."
  value       = azurerm_log_analytics_workspace.this.id
}

output "log_analytics_workspace_name" {
  description = "Log Analytics Workspace name."
  value       = azurerm_log_analytics_workspace.this.name
}

output "log_analytics_workspace_workspace_id" {
  description = "Log Analytics Workspace customer ID."
  value       = azurerm_log_analytics_workspace.this.workspace_id
}

output "application_insights_id" {
  description = "Application Insights component resource ID."
  value       = azurerm_application_insights.this.id
}

output "application_insights_name" {
  description = "Application Insights component name."
  value       = azurerm_application_insights.this.name
}

output "application_insights_connection_string" {
  description = "Application Insights connection string for backend telemetry exporters. The provider marks it sensitive, but DocMind treats it as non-secret runtime configuration."
  value       = nonsensitive(azurerm_application_insights.this.connection_string)
}
