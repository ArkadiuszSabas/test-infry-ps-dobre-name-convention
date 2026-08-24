data "azurerm_resource_group" "environment" {
  name = var.application_resource_group_name
}

locals {
  app_token         = lower(replace(var.app_id, "/[^0-9A-Za-z]/", ""))
  environment_token = lower(replace(var.environment, "/[^0-9A-Za-z]/", ""))
  instance_token    = lower(replace(var.instance_number, "/[^0-9A-Za-z]/", ""))

  cmk_identities = {
    for workload in var.cmk_identity_workloads : workload => {
      name = "id-${local.app_token}-${local.environment_token}-${workload}-${local.instance_token}"
    }
  }
}

module "cmk_identities" {
  source = "../modules/managed-identities"

  location            = var.location
  resource_group_name = data.azurerm_resource_group.environment.name
  identities          = local.cmk_identities
  tags                = var.tags
}
