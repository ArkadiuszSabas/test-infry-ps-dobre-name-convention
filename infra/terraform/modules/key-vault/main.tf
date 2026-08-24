resource "azurerm_key_vault" "this" {
  name                = var.name
  location            = var.location
  resource_group_name = var.resource_group_name
  tenant_id           = var.tenant_id
  sku_name            = "standard"

  rbac_authorization_enabled    = true
  purge_protection_enabled      = var.purge_protection_enabled
  soft_delete_retention_days    = var.soft_delete_retention_days
  public_network_access_enabled = var.public_network_access_enabled

  network_acls {
    bypass         = var.network_acls_bypass
    default_action = var.network_acls_default_action
  }

  tags = var.tags
}

locals {
  role_assignment_uuid_namespace       = "6ba7b811-9dad-11d1-80b4-00c04fd430c8"
  secrets_user_role_definition_name    = "Key Vault Secrets User"
  secrets_officer_role_definition_name = "Key Vault Secrets Officer"
  secrets_officer_principal_types = {
    for principal_name in keys(var.secrets_officer_principal_ids) :
    principal_name => lookup(var.secrets_officer_principal_types, principal_name, var.secrets_officer_principal_type)
  }
}

resource "azurerm_role_assignment" "secrets_user" {
  for_each = var.secrets_user_principal_ids

  name = uuidv5(local.role_assignment_uuid_namespace, lower(join("|", [
    azurerm_key_vault.this.id,
    local.secrets_user_role_definition_name,
    each.value,
    "",
    "true",
  ])))

  scope                            = azurerm_key_vault.this.id
  role_definition_name             = local.secrets_user_role_definition_name
  principal_id                     = each.value
  skip_service_principal_aad_check = true
}

resource "terraform_data" "secrets_officer_assignment_replacement" {
  for_each = var.secrets_officer_principal_ids

  triggers_replace = [
    each.value,
    local.secrets_officer_principal_types[each.key] == null ? "" : local.secrets_officer_principal_types[each.key],
    lookup(var.secrets_officer_skip_service_principal_aad_check_by_principal, each.key, true),
  ]
}

resource "azurerm_role_assignment" "secrets_officer" {
  for_each = var.secrets_officer_principal_ids

  name = uuidv5(local.role_assignment_uuid_namespace, lower(join("|", [
    azurerm_key_vault.this.id,
    local.secrets_officer_role_definition_name,
    each.value,
    local.secrets_officer_principal_types[each.key] == null ? "" : local.secrets_officer_principal_types[each.key],
    tostring(lookup(var.secrets_officer_skip_service_principal_aad_check_by_principal, each.key, true)),
  ])))

  scope                            = azurerm_key_vault.this.id
  role_definition_name             = local.secrets_officer_role_definition_name
  principal_id                     = each.value
  principal_type                   = local.secrets_officer_principal_types[each.key]
  skip_service_principal_aad_check = lookup(var.secrets_officer_skip_service_principal_aad_check_by_principal, each.key, true)

  lifecycle {
    replace_triggered_by = [
      terraform_data.secrets_officer_assignment_replacement[each.key],
    ]
  }
}
