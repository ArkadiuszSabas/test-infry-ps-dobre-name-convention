output "ids" {
  description = "Azure resource IDs for managed identities."
  value       = { for key, identity in azurerm_user_assigned_identity.this : key => identity.id }
}

output "client_ids" {
  description = "Client IDs for managed identities."
  value       = { for key, identity in azurerm_user_assigned_identity.this : key => identity.client_id }
}

output "principal_ids" {
  description = "Principal IDs for managed identities."
  value       = { for key, identity in azurerm_user_assigned_identity.this : key => identity.principal_id }
}
