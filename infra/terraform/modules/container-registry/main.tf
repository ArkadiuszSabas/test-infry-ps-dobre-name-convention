resource "azurerm_container_registry" "this" {
  name                = var.name
  location            = var.location
  resource_group_name = var.resource_group_name

  sku           = var.sku
  admin_enabled = false

  public_network_access_enabled = false
  tags                          = var.tags
}

locals {
  role_assignment_uuid_namespace = "6ba7b811-9dad-11d1-80b4-00c04fd430c8"
  acr_pull_role_definition       = "AcrPull"
  acr_push_role_definition       = "AcrPush"
}

resource "azurerm_role_assignment" "pull" {
  for_each = var.pull_principal_ids

  name = uuidv5(local.role_assignment_uuid_namespace, lower(join("|", [
    azurerm_container_registry.this.id,
    local.acr_pull_role_definition,
    each.value,
    "",
    "true",
  ])))

  scope                            = azurerm_container_registry.this.id
  role_definition_name             = local.acr_pull_role_definition
  principal_id                     = each.value
  skip_service_principal_aad_check = true
}

resource "azurerm_role_assignment" "push" {
  for_each = var.push_principal_ids

  name = uuidv5(local.role_assignment_uuid_namespace, lower(join("|", [
    azurerm_container_registry.this.id,
    local.acr_push_role_definition,
    each.value,
    "",
    "true",
  ])))

  scope                            = azurerm_container_registry.this.id
  role_definition_name             = local.acr_push_role_definition
  principal_id                     = each.value
  skip_service_principal_aad_check = true
}
