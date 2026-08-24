data "azurerm_key_vault" "cmk" {
  name                = var.key_vault_name
  resource_group_name = var.key_vault_resource_group_name
}

data "azurerm_user_assigned_identity" "cmk" {
  for_each = var.cmk_identities

  name                = each.value.name
  resource_group_name = var.application_resource_group_name
}

locals {
  role_assignment_uuid_namespace = "6ba7b811-9dad-11d1-80b4-00c04fd430c8"
}

resource "azurerm_role_assignment" "cmk_crypto_service_encryption_user" {
  for_each = data.azurerm_user_assigned_identity.cmk

  name = uuidv5(local.role_assignment_uuid_namespace, lower(join("|", [
    data.azurerm_key_vault.cmk.id,
    "Key Vault Crypto Service Encryption User",
    each.value.principal_id,
    "ServicePrincipal",
    "true",
  ])))

  scope                            = data.azurerm_key_vault.cmk.id
  role_definition_name             = "Key Vault Crypto Service Encryption User"
  principal_id                     = each.value.principal_id
  principal_type                   = "ServicePrincipal"
  skip_service_principal_aad_check = true
}
