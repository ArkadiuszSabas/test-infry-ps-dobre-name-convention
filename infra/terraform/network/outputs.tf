output "virtual_network_id" {
  value       = data.azurerm_virtual_network.existing.id
  description = "Existing ProService VNet resource ID."
}

output "container_apps_infrastructure_subnet_id" {
  value       = data.azurerm_subnet.container_apps_infrastructure.id
  description = "Existing Container Apps subnet ID passed to the core root."
}

output "private_endpoint_subnet_id" {
  value       = data.azurerm_subnet.private_endpoints.id
  description = "Existing Private Endpoint subnet ID."
}

output "private_dns_zone_ids" {
  value       = { for key, zone in data.azurerm_private_dns_zone.this : key => zone.id }
  description = "Private DNS zone IDs used by the network completion phase."
}

output "private_endpoint_ip_addresses" {
  value       = module.private_endpoints.private_endpoint_ip_addresses
  description = "Private Endpoint addresses for DNS and routing verification."
}
