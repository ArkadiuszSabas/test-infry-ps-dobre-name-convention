data "azurerm_resource_group" "environment" {
  name = var.application_resource_group_name
}

module "cmk_identities" {
  source = "../modules/managed-identities"

  location            = var.location
  resource_group_name = data.azurerm_resource_group.environment.name
  identities          = var.cmk_identities
  tags                = var.tags
}
