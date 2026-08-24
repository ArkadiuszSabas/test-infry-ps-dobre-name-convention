resource "azurerm_storage_account" "this" {
  count = var.enabled ? 1 : 0

  name                            = var.storage_account_name
  resource_group_name             = var.resource_group_name
  location                        = var.location
  account_tier                    = "Standard"
  account_replication_type        = "LRS"
  account_kind                    = "StorageV2"
  min_tls_version                 = "TLS1_2"
  public_network_access_enabled   = false
  shared_access_key_enabled       = true
  allow_nested_items_to_be_public = false

  blob_properties {
    versioning_enabled = false
    delete_retention_policy {
      days = 7
    }
    container_delete_retention_policy {
      days = 7
    }
  }

  tags = var.tags

  lifecycle {
    prevent_destroy = true
  }
}

resource "azapi_resource" "blob_container" {
  count = var.enabled ? 1 : 0

  type      = "Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01"
  name      = local.blob_container_name
  parent_id = "${azurerm_storage_account.this[0].id}/blobServices/default"
  body = {
    properties = {
      publicAccess = "None"
    }
  }

  lifecycle {
    prevent_destroy = true
  }
}

resource "azurerm_storage_management_policy" "events" {
  count = var.enabled ? 1 : 0

  storage_account_id = azurerm_storage_account.this[0].id

  rule {
    name    = "expire-langfuse-events"
    enabled = true

    filters {
      prefix_match = ["${local.blob_container_name}/events/"]
      blob_types   = ["blockBlob"]
    }

    actions {
      base_blob {
        delete_after_days_since_modification_greater_than = var.event_blob_retention_days
      }
    }
  }

  depends_on = [azapi_resource.blob_container]
}

resource "azurerm_storage_account" "clickhouse" {
  count = var.enabled ? 1 : 0

  name                            = var.clickhouse_storage_account_name
  resource_group_name             = var.resource_group_name
  location                        = var.location
  account_tier                    = "Premium"
  account_replication_type        = "LRS"
  account_kind                    = "FileStorage"
  min_tls_version                 = "TLS1_2"
  https_traffic_only_enabled      = false
  public_network_access_enabled   = false
  shared_access_key_enabled       = false
  allow_nested_items_to_be_public = false

  tags = var.tags

  lifecycle {
    prevent_destroy = true
  }
}

resource "azapi_resource" "clickhouse_share" {
  count = var.enabled ? 1 : 0

  type      = "Microsoft.Storage/storageAccounts/fileServices/shares@2023-05-01"
  name      = local.clickhouse_share_name
  parent_id = "${azurerm_storage_account.clickhouse[0].id}/fileServices/default"
  body = {
    properties = {
      enabledProtocols = "NFS"
      rootSquash       = "NoRootSquash"
      shareQuota       = var.clickhouse_share_quota_gb
    }
  }

  lifecycle {
    prevent_destroy = true
  }
}

resource "azapi_resource" "postgres_share" {
  count = var.enabled ? 1 : 0

  type      = "Microsoft.Storage/storageAccounts/fileServices/shares@2023-05-01"
  name      = local.postgres_share_name
  parent_id = "${azurerm_storage_account.clickhouse[0].id}/fileServices/default"
  body = {
    properties = {
      enabledProtocols = "NFS"
      rootSquash       = "NoRootSquash"
      shareQuota       = var.postgres_share_quota_gb
    }
  }

  lifecycle {
    prevent_destroy = true
  }
}

resource "azapi_resource" "valkey_share" {
  count = var.enabled ? 1 : 0

  type      = "Microsoft.Storage/storageAccounts/fileServices/shares@2023-05-01"
  name      = local.valkey_share_name
  parent_id = "${azurerm_storage_account.clickhouse[0].id}/fileServices/default"
  body = {
    properties = {
      enabledProtocols = "NFS"
      rootSquash       = "NoRootSquash"
      shareQuota       = var.valkey_share_quota_gb
    }
  }

  lifecycle {
    prevent_destroy = true
  }
}

resource "azurerm_private_endpoint" "blob" {
  count = var.enabled ? 1 : 0

  name                = "pep-${var.workloads.web.name}-blob"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.private_endpoint_subnet_id

  private_service_connection {
    name                           = "psc-${var.workloads.web.name}-blob"
    private_connection_resource_id = azurerm_storage_account.this[0].id
    is_manual_connection           = false
    subresource_names              = ["blob"]
  }

  private_dns_zone_group {
    name                 = "default"
    private_dns_zone_ids = [var.storage_blob_private_dns_zone_id]
  }

  tags = var.tags
}

resource "azurerm_private_endpoint" "clickhouse_file" {
  count = var.enabled ? 1 : 0

  name                = "pep-${var.workloads.clickhouse.name}-file"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.private_endpoint_subnet_id

  private_service_connection {
    name                           = "psc-${var.workloads.clickhouse.name}-file"
    private_connection_resource_id = azurerm_storage_account.clickhouse[0].id
    is_manual_connection           = false
    subresource_names              = ["file"]
  }

  private_dns_zone_group {
    name                 = "default"
    private_dns_zone_ids = [var.storage_file_private_dns_zone_id]
  }

  tags = var.tags
}

resource "azapi_resource" "clickhouse_environment_storage" {
  count = var.enabled ? 1 : 0

  type      = "Microsoft.App/managedEnvironments/storages@2025-01-01"
  name      = local.clickhouse_storage_name
  parent_id = var.container_app_environment_id
  body = {
    properties = {
      nfsAzureFile = {
        accessMode = "ReadWrite"
        server     = "${azurerm_storage_account.clickhouse[0].name}.file.core.windows.net"
        shareName  = "/${azurerm_storage_account.clickhouse[0].name}/${local.clickhouse_share_name}"
      }
    }
  }

  depends_on = [
    azapi_resource.clickhouse_share,
    azurerm_private_endpoint.clickhouse_file,
  ]
}

resource "azapi_resource" "postgres_environment_storage" {
  count = var.enabled ? 1 : 0

  type      = "Microsoft.App/managedEnvironments/storages@2025-01-01"
  name      = local.postgres_storage_name
  parent_id = var.container_app_environment_id
  body = {
    properties = {
      nfsAzureFile = {
        accessMode = "ReadWrite"
        server     = "${azurerm_storage_account.clickhouse[0].name}.file.core.windows.net"
        shareName  = "/${azurerm_storage_account.clickhouse[0].name}/${local.postgres_share_name}"
      }
    }
  }

  depends_on = [
    azapi_resource.postgres_share,
    azurerm_private_endpoint.clickhouse_file,
  ]
}

resource "azapi_resource" "valkey_environment_storage" {
  count = var.enabled ? 1 : 0

  type      = "Microsoft.App/managedEnvironments/storages@2025-01-01"
  name      = local.valkey_storage_name
  parent_id = var.container_app_environment_id
  body = {
    properties = {
      nfsAzureFile = {
        accessMode = "ReadWrite"
        server     = "${azurerm_storage_account.clickhouse[0].name}.file.core.windows.net"
        shareName  = "/${azurerm_storage_account.clickhouse[0].name}/${local.valkey_share_name}"
      }
    }
  }

  depends_on = [
    azapi_resource.valkey_share,
    azurerm_private_endpoint.clickhouse_file,
  ]
}
