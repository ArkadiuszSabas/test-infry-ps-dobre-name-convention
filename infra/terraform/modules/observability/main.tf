locals {
  creates_monitor_private_link_scope = var.shared_monitor_private_link_scope_resource_group_name == null
  monitor_private_link_scope_resource_group_name = coalesce(
    var.shared_monitor_private_link_scope_resource_group_name,
    var.resource_group_name,
  )
  scoped_service_name_suffix = var.scoped_service_name_suffix == null ? "" : "-${var.scoped_service_name_suffix}"
}

moved {
  from = azurerm_monitor_private_link_scope.this
  to   = azurerm_monitor_private_link_scope.this[0]
}

resource "azurerm_log_analytics_workspace" "this" {
  name                = var.log_analytics_workspace_name
  location            = var.location
  resource_group_name = var.resource_group_name

  sku               = "PerGB2018"
  retention_in_days = var.retention_in_days
  daily_quota_gb    = var.daily_quota_gb

  internet_ingestion_enabled = false
  internet_query_enabled     = false

  tags = var.tags
}

resource "azurerm_monitor_private_link_scope" "this" {
  count = local.creates_monitor_private_link_scope ? 1 : 0

  name                  = var.monitor_private_link_scope_name
  resource_group_name   = var.resource_group_name
  ingestion_access_mode = "PrivateOnly"
  query_access_mode     = "PrivateOnly"
  tags                  = var.tags
}

resource "azurerm_application_insights" "this" {
  name                = var.application_insights_name
  location            = var.location
  resource_group_name = var.resource_group_name

  application_type = "web"
  workspace_id     = azurerm_log_analytics_workspace.this.id

  internet_ingestion_enabled = false
  internet_query_enabled     = false

  tags = var.tags
}

resource "azurerm_monitor_private_link_scoped_service" "log_analytics" {
  name                = "log-analytics${local.scoped_service_name_suffix}"
  resource_group_name = local.monitor_private_link_scope_resource_group_name
  scope_name          = var.monitor_private_link_scope_name
  linked_resource_id  = azurerm_log_analytics_workspace.this.id

  depends_on = [azurerm_monitor_private_link_scope.this]
}

resource "azurerm_monitor_private_link_scoped_service" "application_insights" {
  name                = "application-insights${local.scoped_service_name_suffix}"
  resource_group_name = local.monitor_private_link_scope_resource_group_name
  scope_name          = var.monitor_private_link_scope_name
  linked_resource_id  = azurerm_application_insights.this.id

  depends_on = [azurerm_monitor_private_link_scope.this]
}
