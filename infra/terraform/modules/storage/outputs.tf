output "id" {
  description = "Storage Account resource ID."
  value       = azurerm_storage_account.this.id
}

output "name" {
  description = "Storage Account name."
  value       = azurerm_storage_account.this.name
}

output "primary_blob_endpoint" {
  description = "Primary blob endpoint."
  value       = azurerm_storage_account.this.primary_blob_endpoint
}

output "container_names" {
  description = "Blob container names."
  value       = [for container in azurerm_storage_container.this : container.name]
}
