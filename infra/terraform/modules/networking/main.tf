locals {
  private_dns_zones = {
    cognitive_services  = "privatelink.cognitiveservices.azure.com"
    container_apps      = "privatelink.${var.location}.azurecontainerapps.io"
    foundry_openai      = "privatelink.openai.azure.com"
    foundry_services_ai = "privatelink.services.ai.azure.com"
    key_vault           = "privatelink.vaultcore.azure.net"
    postgresql          = "privatelink.postgres.database.azure.com"
    storage_blob        = "privatelink.blob.core.windows.net"
    storage_file        = "privatelink.file.core.windows.net"
  }

  additional_container_apps_private_dns_zones = {
    for location in var.additional_container_apps_private_dns_locations :
    "container_apps_${location}" => "privatelink.${location}.azurecontainerapps.io"
    if location != var.location
  }
  configured_private_dns_zones = merge(local.private_dns_zones, local.additional_container_apps_private_dns_zones)

  uses_shared_private_dns = var.shared_private_dns_resource_group_name != null
  effective_private_dns_zones = local.uses_shared_private_dns ? {
    for key, zone in data.azurerm_private_dns_zone.shared : key => {
      id                  = zone.id
      name                = zone.name
      resource_group_name = var.shared_private_dns_resource_group_name
    }
    } : {
    for key, zone in azurerm_private_dns_zone.this : key => {
      id                  = zone.id
      name                = zone.name
      resource_group_name = var.resource_group_name
    }
  }
}

resource "azurerm_virtual_network" "this" {
  name                = var.virtual_network_name
  location            = var.location
  resource_group_name = var.resource_group_name
  address_space       = var.address_space

  tags = var.tags
}

resource "azurerm_subnet" "private_endpoints" {
  name                              = var.private_endpoint_subnet_name
  resource_group_name               = var.resource_group_name
  virtual_network_name              = azurerm_virtual_network.this.name
  address_prefixes                  = [var.private_endpoint_subnet_cidr]
  private_endpoint_network_policies = "Disabled"
}

resource "azurerm_subnet" "container_apps_infrastructure" {
  name                 = var.container_apps_infrastructure_subnet_name
  resource_group_name  = var.resource_group_name
  virtual_network_name = azurerm_virtual_network.this.name
  address_prefixes     = [var.container_apps_infrastructure_subnet_cidr]

  delegation {
    name = "container-apps-environments"

    service_delegation {
      name = "Microsoft.App/environments"
      actions = [
        "Microsoft.Network/virtualNetworks/subnets/join/action",
      ]
    }
  }
}

resource "azurerm_subnet" "openvpn_server" {
  name                              = var.openvpn_server_subnet_name
  resource_group_name               = var.resource_group_name
  virtual_network_name              = azurerm_virtual_network.this.name
  address_prefixes                  = [var.openvpn_server_subnet_cidr]
  private_endpoint_network_policies = "Disabled"
}

resource "azurerm_private_dns_zone" "this" {
  for_each = local.uses_shared_private_dns ? {} : local.configured_private_dns_zones

  name                = each.value
  resource_group_name = var.resource_group_name
  tags                = var.tags
}

data "azurerm_private_dns_zone" "shared" {
  for_each = local.uses_shared_private_dns ? local.configured_private_dns_zones : {}

  name                = each.value
  resource_group_name = var.shared_private_dns_resource_group_name
}

resource "azurerm_private_dns_zone_virtual_network_link" "this" {
  for_each = local.effective_private_dns_zones

  name = local.uses_shared_private_dns ? (
    "pdnslink-${replace(each.key, "_", "-")}-${var.virtual_network_name}"
  ) : "pdnslink-${replace(each.key, "_", "-")}"
  resource_group_name   = each.value.resource_group_name
  private_dns_zone_name = each.value.name
  virtual_network_id    = azurerm_virtual_network.this.id
  registration_enabled  = false
  tags                  = var.tags
}
