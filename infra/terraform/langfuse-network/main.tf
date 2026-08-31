locals {
  tenant_token                        = lower(replace(var.tenant_prefix, "/[^0-9A-Za-z]/", ""))
  app_token                           = lower(replace(var.app_id, "/[^0-9A-Za-z]/", ""))
  environment_token                   = lower(replace(var.environment, "/[^0-9A-Za-z]/", ""))
  instance_token                      = lower(replace(var.instance_number, "/[^0-9A-Za-z]/", ""))
  langfuse_storage_account_name       = "${local.tenant_token}st${local.app_token}lfblob${local.environment_token}${local.instance_token}"
  langfuse_files_storage_account_name = "${local.tenant_token}st${local.app_token}lffile${local.environment_token}${local.instance_token}"
}

data "azurerm_resource_group" "network" {
  name = var.network_resource_group_name
}

data "azurerm_virtual_network" "this" {
  name                = var.virtual_network_name
  resource_group_name = data.azurerm_resource_group.network.name
}

data "azurerm_subnet" "private_endpoints" {
  name                 = var.private_endpoint_subnet_name
  virtual_network_name = data.azurerm_virtual_network.this.name
  resource_group_name  = data.azurerm_resource_group.network.name
}

data "azurerm_storage_account" "blob" {
  name                = local.langfuse_storage_account_name
  resource_group_name = var.application_resource_group_name
}

data "azurerm_storage_account" "files" {
  name                = local.langfuse_files_storage_account_name
  resource_group_name = var.application_resource_group_name
}

data "azurerm_private_dns_zone" "blob" {
  provider            = azurerm.hub
  name                = "privatelink.blob.core.windows.net"
  resource_group_name = var.private_dns_resource_group_name
}

data "azurerm_private_dns_zone" "files" {
  provider            = azurerm.hub
  name                = "privatelink.file.core.windows.net"
  resource_group_name = var.private_dns_resource_group_name
}

module "private_endpoints" {
  source = "../modules/private-endpoints"

  location            = var.location
  resource_group_name = data.azurerm_resource_group.network.name
  private_endpoints = {
    langfuse-blob = {
      name                           = "pep-${local.app_token}-${local.environment_token}-langfuse-blob-${local.instance_token}"
      subnet_id                      = data.azurerm_subnet.private_endpoints.id
      private_connection_resource_id = data.azurerm_storage_account.blob.id
      subresource_names              = ["blob"]
      private_dns_zone_ids           = [data.azurerm_private_dns_zone.blob.id]
    }
    langfuse-files = {
      name                           = "pep-${local.app_token}-${local.environment_token}-langfuse-files-${local.instance_token}"
      subnet_id                      = data.azurerm_subnet.private_endpoints.id
      private_connection_resource_id = data.azurerm_storage_account.files.id
      subresource_names              = ["file"]
      private_dns_zone_ids           = [data.azurerm_private_dns_zone.files.id]
    }
  }
  tags = var.tags
}

output "private_endpoint_ids" {
  value = module.private_endpoints.private_endpoint_ids
}
