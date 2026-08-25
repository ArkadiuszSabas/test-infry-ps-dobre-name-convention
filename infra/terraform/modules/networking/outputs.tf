output "virtual_network_id" {
  description = "Environment virtual network resource ID."
  value       = azurerm_virtual_network.this.id
}

output "virtual_network_name" {
  description = "Environment virtual network name."
  value       = azurerm_virtual_network.this.name
}

output "private_endpoint_subnet_id" {
  description = "Subnet ID for application service Private Endpoints."
  value       = azurerm_subnet.private_endpoints.id
}

output "container_apps_infrastructure_subnet_id" {
  description = "Subnet ID delegated to Azure Container Apps environments."
  value       = azurerm_subnet.container_apps_infrastructure.id
}

output "openvpn_server_subnet_id" {
  description = "Subnet ID for the optional OpenVPN server VM."
  value       = azurerm_subnet.openvpn_server.id
}

output "private_dns_zone_ids" {
  description = "Private DNS zone IDs keyed by logical service name."
  value       = { for key, zone in local.effective_private_dns_zones : key => zone.id }
}

output "private_dns_zone_names" {
  description = "Private DNS zone names keyed by logical service name."
  value       = { for key, zone in local.effective_private_dns_zones : key => zone.name }
}

output "private_dns_zone_resource_group_names" {
  description = "Private DNS zone resource group names keyed by logical service name."
  value       = { for key, zone in local.effective_private_dns_zones : key => zone.resource_group_name }
}
