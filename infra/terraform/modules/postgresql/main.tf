resource "azurerm_postgresql_flexible_server" "this" {
  name                = var.name
  location            = var.location
  resource_group_name = var.resource_group_name

  version                       = var.postgresql_version
  sku_name                      = var.sku_name
  zone                          = var.zone
  storage_mb                    = var.storage_mb
  auto_grow_enabled             = true
  backup_retention_days         = var.backup_retention_days
  geo_redundant_backup_enabled  = var.geo_redundant_backup_enabled
  public_network_access_enabled = var.public_network_access_enabled

  identity {
    type         = "SystemAssigned, UserAssigned"
    identity_ids = [var.cmk_user_assigned_identity_id]
  }

  customer_managed_key {
    key_vault_key_id                  = var.cmk_key_vault_key_id
    primary_user_assigned_identity_id = var.cmk_user_assigned_identity_id
  }

  authentication {
    active_directory_auth_enabled = true
    password_auth_enabled         = false
    tenant_id                     = var.tenant_id
  }

  maintenance_window {
    day_of_week  = 0
    start_hour   = 2
    start_minute = 0
  }

  tags = var.tags
}

resource "azurerm_postgresql_flexible_server_active_directory_administrator" "this" {
  server_name         = azurerm_postgresql_flexible_server.this.name
  resource_group_name = var.resource_group_name
  tenant_id           = var.tenant_id
  object_id           = var.active_directory_administrator.object_id
  principal_name      = var.active_directory_administrator.principal_name
  principal_type      = var.active_directory_administrator.principal_type
}

resource "azurerm_postgresql_flexible_server_database" "this" {
  for_each = var.database_names

  name      = each.value
  server_id = azurerm_postgresql_flexible_server.this.id
  charset   = "UTF8"
  collation = "en_US.utf8"
}

resource "azurerm_postgresql_flexible_server_configuration" "timezone" {
  name      = "timezone"
  server_id = azurerm_postgresql_flexible_server.this.id
  value     = "UTC"
}

resource "azurerm_postgresql_flexible_server_firewall_rule" "container_apps" {
  for_each = var.firewall_ip_addresses

  name             = "container-app-${replace(each.value, ".", "-")}"
  server_id        = azurerm_postgresql_flexible_server.this.id
  start_ip_address = each.value
  end_ip_address   = each.value
}
