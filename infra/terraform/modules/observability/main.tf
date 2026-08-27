resource "azurerm_log_analytics_workspace" "this" {
  name                = var.log_analytics_workspace_name
  location            = var.location
  resource_group_name = var.resource_group_name

  sku               = "PerGB2018"
  retention_in_days = var.retention_in_days
  daily_quota_gb    = var.daily_quota_gb

  internet_ingestion_enabled = true
  internet_query_enabled     = true

  tags = var.tags
}

resource "azurerm_application_insights" "this" {
  name                = var.application_insights_name
  location            = var.location
  resource_group_name = var.resource_group_name

  application_type = "web"
  workspace_id     = azurerm_log_analytics_workspace.this.id

  internet_ingestion_enabled = true
  internet_query_enabled     = true

  tags = var.tags
}
