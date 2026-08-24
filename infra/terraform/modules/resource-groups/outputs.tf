output "environment_resource_group_name" {
  description = "Environment resource group name."
  value       = azurerm_resource_group.environment.name
}

output "environment_resource_group_id" {
  description = "Environment resource group resource ID."
  value       = azurerm_resource_group.environment.id
}
