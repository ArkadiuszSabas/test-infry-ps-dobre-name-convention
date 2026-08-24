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

output "monitor_private_link_scope_id" {
  description = "Azure Monitor Private Link Scope resource ID when the module owns the scope."
  value       = try(azurerm_monitor_private_link_scope.this[0].id, null)
}

output "monitor_private_link_scope_name" {
  description = "Effective Azure Monitor Private Link Scope name."
  value       = var.monitor_private_link_scope_name
}
