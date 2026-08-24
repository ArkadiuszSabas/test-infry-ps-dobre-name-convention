resource "azurerm_storage_account" "this" {
  name                = var.name
  location            = var.location
  resource_group_name = var.resource_group_name

  account_kind             = "StorageV2"
  account_tier             = "Standard"
  account_replication_type = var.replication_type

  allow_nested_items_to_be_public = false
  default_to_oauth_authentication = var.default_to_oauth_authentication
  https_traffic_only_enabled      = true
  min_tls_version                 = "TLS1_2"
  public_network_access_enabled   = var.public_network_access_enabled
  shared_access_key_enabled       = var.shared_access_key_enabled

  identity {
    type         = "UserAssigned"
    identity_ids = [var.cmk_user_assigned_identity_id]
  }

  customer_managed_key {
    key_vault_key_id          = var.cmk_key_vault_key_id
    user_assigned_identity_id = var.cmk_user_assigned_identity_id
  }

  blob_properties {
    versioning_enabled = true

    delete_retention_policy {
      days = 7
    }

    container_delete_retention_policy {
      days = 7
    }
  }

  tags = var.tags
}

resource "azurerm_storage_container" "this" {
  for_each = var.containers

  name                  = each.value
  storage_account_id    = azurerm_storage_account.this.id
  container_access_type = "private"
}

locals {
  role_assignment_uuid_namespace        = "6ba7b811-9dad-11d1-80b4-00c04fd430c8"
  blob_data_contributor_role_definition = "Storage Blob Data Contributor"

  blob_data_contributor_assignments = merge([
    for workload, assignment in var.blob_data_contributor_assignments : {
      for container_name in assignment.container_names : "${workload}-${container_name}" => {
        container_name                   = container_name
        principal_id                     = assignment.principal_id
        principal_type                   = assignment.principal_type
        skip_service_principal_aad_check = assignment.skip_service_principal_aad_check
      }
    }
  ]...)
}

resource "terraform_data" "blob_data_contributor_assignment_replacement" {
  for_each = local.blob_data_contributor_assignments

  triggers_replace = [
    each.value.principal_id,
    each.value.skip_service_principal_aad_check,
  ]
}

resource "azurerm_role_assignment" "blob_data_contributor" {
  for_each = local.blob_data_contributor_assignments

  name = uuidv5(local.role_assignment_uuid_namespace, lower(join("|", [
    azurerm_storage_container.this[each.value.container_name].resource_manager_id,
    local.blob_data_contributor_role_definition,
    each.value.principal_id,
    each.value.principal_type == null ? "" : each.value.principal_type,
    tostring(each.value.skip_service_principal_aad_check),
  ])))

  scope                            = azurerm_storage_container.this[each.value.container_name].resource_manager_id
  role_definition_name             = local.blob_data_contributor_role_definition
  principal_id                     = each.value.principal_id
  principal_type                   = each.value.principal_type
  skip_service_principal_aad_check = each.value.skip_service_principal_aad_check

  lifecycle {
    replace_triggered_by = [
      terraform_data.blob_data_contributor_assignment_replacement[each.key],
    ]
  }
}
