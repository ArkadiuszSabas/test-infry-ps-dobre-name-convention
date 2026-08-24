output "private_endpoint_ids" {
  description = "Private Endpoint IDs keyed by logical endpoint name."
  value       = { for key, endpoint in azurerm_private_endpoint.this : key => endpoint.id }
}

output "private_endpoint_ip_addresses" {
  description = "Private Endpoint private IP addresses keyed by logical endpoint name."
  value = {
    for key, endpoint in azurerm_private_endpoint.this :
    key => endpoint.private_service_connection[0].private_ip_address
  }
}
