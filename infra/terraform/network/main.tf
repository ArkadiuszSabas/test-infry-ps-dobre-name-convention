data "azurerm_resource_group" "network" {
  name = var.network_resource_group_name
}

data "azurerm_resource_group" "application" {
  name = var.application_resource_group_name
}

data "azurerm_virtual_network" "existing" {
  name                = var.virtual_network_name
  resource_group_name = data.azurerm_resource_group.network.name
}

data "azurerm_subnet" "container_apps_infrastructure" {
  name                 = var.container_apps_infrastructure_subnet_name
  virtual_network_name = data.azurerm_virtual_network.existing.name
  resource_group_name  = data.azurerm_resource_group.network.name
}

data "azurerm_subnet" "private_endpoints" {
  name                 = var.private_endpoint_subnet_name
  virtual_network_name = data.azurerm_virtual_network.existing.name
  resource_group_name  = data.azurerm_resource_group.network.name
}

data "azapi_resource" "container_apps_infrastructure_subnet" {
  type                   = "Microsoft.Network/virtualNetworks/subnets@2024-05-01"
  resource_id            = data.azurerm_subnet.container_apps_infrastructure.id
  response_export_values = ["properties.delegations"]
}

locals {
  tenant_token      = lower(replace(var.tenant_prefix, "/[^0-9A-Za-z]/", ""))
  app_token         = lower(replace(var.app_id, "/[^0-9A-Za-z]/", ""))
  environment_token = lower(replace(var.environment, "/[^0-9A-Za-z]/", ""))
  instance_token    = lower(replace(var.instance_number, "/[^0-9A-Za-z]/", ""))

  private_endpoint_workloads = {
    "key-vault"             = "kv"
    "storage-blob"          = "stblob"
    "service-bus"           = "sb"
    "postgresql"            = "psql"
    "document-intelligence" = "di"
    "foundry"               = "foundry"
    "azure-monitor"         = "ampls"
    "container-apps"        = "cae"
  }

  private_dns_zone_names = {
    azure_monitor       = "privatelink.monitor.azure.com"
    azure_monitor_agent = "privatelink.agentsvc.azure-automation.net"
    azure_monitor_ods   = "privatelink.ods.opinsights.azure.com"
    azure_monitor_oms   = "privatelink.oms.opinsights.azure.com"
    cognitive_services  = "privatelink.cognitiveservices.azure.com"
    container_apps      = "privatelink.${var.location}.azurecontainerapps.io"
    foundry_openai      = "privatelink.openai.azure.com"
    foundry_services_ai = "privatelink.services.ai.azure.com"
    key_vault           = "privatelink.vaultcore.azure.net"
    postgresql          = "privatelink.postgres.database.azure.com"
    service_bus         = "privatelink.servicebus.windows.net"
    storage_blob        = "privatelink.blob.core.windows.net"
  }

  additional_container_apps_private_dns_zone_names = {
    for location in var.additional_container_apps_private_dns_locations :
    "container_apps_${location}" => "privatelink.${location}.azurecontainerapps.io"
    if location != var.location
  }

  configured_private_dns_zone_names = merge(
    local.private_dns_zone_names,
    local.additional_container_apps_private_dns_zone_names,
  )

  container_apps_delegations = toset([
    for delegation in try(data.azapi_resource.container_apps_infrastructure_subnet.output.properties.delegations, []) :
    delegation.properties.serviceName
  ])

  container_apps_environment_private_dns = var.container_apps_environment_private_dns == null ? {} : {
    (var.container_apps_environment_private_dns.private_endpoint_key) = {
      default_domain        = var.container_apps_environment_private_dns.default_domain
      private_dns_zone_key  = var.container_apps_environment_private_dns.private_dns_zone_key
      default_domain_prefix = split(".", var.container_apps_environment_private_dns.default_domain)[0]
    }
  }
}

resource "terraform_data" "approved_design_guard" {
  lifecycle {
    precondition {
      condition     = var.network_design_approved
      error_message = "ProService network design must be approved before planning this root."
    }

    precondition {
      condition     = toset(data.azurerm_virtual_network.existing.address_space) == toset(var.expected_network_address_space)
      error_message = "The existing ProService VNet address space does not match expected_network_address_space."
    }

    precondition {
      condition     = toset(data.azurerm_subnet.container_apps_infrastructure.address_prefixes) == toset([var.expected_container_apps_infrastructure_subnet_cidr])
      error_message = "The existing Container Apps subnet CIDR does not match the reviewed value."
    }

    precondition {
      condition     = toset(data.azurerm_subnet.private_endpoints.address_prefixes) == toset([var.expected_private_endpoint_subnet_cidr])
      error_message = "The existing Private Endpoint subnet CIDR does not match the reviewed value."
    }

    precondition {
      condition     = contains(local.container_apps_delegations, "Microsoft.App/environments")
      error_message = "The existing Container Apps subnet must be delegated to Microsoft.App/environments before this root is planned."
    }

    precondition {
      condition = var.container_apps_environment_private_dns == null ? true : try(
        contains(
          var.private_endpoints[var.container_apps_environment_private_dns.private_endpoint_key].subresource_names,
          "managedEnvironments",
        ),
        false,
      )
      error_message = "Container Apps private DNS must reference a managedEnvironments Private Endpoint declared in private_endpoints."
    }

    precondition {
      condition = length([
        for endpoint in values(var.private_endpoints) : endpoint
        if contains(endpoint.subresource_names, "managedEnvironments")
      ]) == 0 || var.container_apps_environment_private_dns != null
      error_message = "A managedEnvironments Private Endpoint requires Container Apps environment private DNS configuration."
    }

    precondition {
      condition = alltrue([
        for endpoint in values(var.private_endpoints) :
        !contains(endpoint.subresource_names, "managedEnvironments") || length(endpoint.private_dns_zone_ids) == 0
      ])
      error_message = "Container Apps Environment Private Endpoints must leave private_dns_zone_ids empty because this root owns the required apex and wildcard A records."
    }

    precondition {
      condition = length([
        for endpoint in values(var.private_endpoints) : endpoint
        if contains(endpoint.subresource_names, "managedEnvironments")
      ]) <= 1
      error_message = "This network root supports at most one Container Apps Environment Private Endpoint per environment."
    }

    precondition {
      condition = alltrue([
        for endpoint in values(var.private_endpoints) : startswith(
          lower(endpoint.private_connection_resource_id),
          lower("${data.azurerm_resource_group.application.id}/providers/"),
        )
      ])
      error_message = "Every Private Endpoint target must belong to the configured application resource group."
    }

    precondition {
      condition = alltrue([
        for endpoint_key in keys(var.private_endpoints) :
        contains(keys(local.private_endpoint_workloads), endpoint_key)
      ])
      error_message = "Every Private Endpoint key must have an approved naming-convention workload token."
    }
  }
}

data "azurerm_private_dns_zone" "this" {
  for_each = local.configured_private_dns_zone_names

  name                = each.value
  resource_group_name = var.private_dns_resource_group_name
}

resource "azurerm_private_dns_zone_virtual_network_link" "this" {
  for_each = data.azurerm_private_dns_zone.this

  name                  = "pdnslink-${var.virtual_network_name}-${replace(each.key, "_", "-")}"
  resource_group_name   = each.value.resource_group_name
  private_dns_zone_name = each.value.name
  virtual_network_id    = data.azurerm_virtual_network.existing.id
  registration_enabled  = false
  tags                  = var.tags
}

module "private_endpoints" {
  source = "../modules/private-endpoints"

  location            = var.location
  resource_group_name = data.azurerm_resource_group.network.name
  private_endpoints = {
    for key, endpoint in var.private_endpoints : key => {
      name                           = "pep-${local.app_token}-${local.environment_token}-${local.private_endpoint_workloads[key]}-${local.instance_token}"
      subnet_id                      = data.azurerm_subnet.private_endpoints.id
      private_connection_resource_id = endpoint.private_connection_resource_id
      subresource_names              = endpoint.subresource_names
      private_dns_zone_ids           = endpoint.private_dns_zone_ids
    }
  }
  tags = var.tags

  depends_on = [terraform_data.approved_design_guard]
}

resource "azurerm_private_dns_a_record" "container_apps_environment" {
  for_each = local.container_apps_environment_private_dns

  name                = each.value.default_domain_prefix
  zone_name           = data.azurerm_private_dns_zone.this[each.value.private_dns_zone_key].name
  resource_group_name = data.azurerm_private_dns_zone.this[each.value.private_dns_zone_key].resource_group_name
  ttl                 = 300
  records             = [module.private_endpoints.private_endpoint_ip_addresses[each.key]]
  tags                = var.tags
}

resource "azurerm_private_dns_a_record" "container_apps_environment_wildcard" {
  for_each = local.container_apps_environment_private_dns

  name                = "*.${each.value.default_domain_prefix}"
  zone_name           = data.azurerm_private_dns_zone.this[each.value.private_dns_zone_key].name
  resource_group_name = data.azurerm_private_dns_zone.this[each.value.private_dns_zone_key].resource_group_name
  ttl                 = 300
  records             = [module.private_endpoints.private_endpoint_ip_addresses[each.key]]
  tags                = var.tags
}
