output "cmk_identity_principal_ids" {
  description = "Principal IDs granted Key Vault Crypto Service Encryption User."
  value       = { for key, identity in data.azurerm_user_assigned_identity.cmk : key => identity.principal_id }
}

output "cmk_role_assignment_ids" {
  description = "Role assignment IDs created on the CMK Key Vault."
  value       = { for key, assignment in azurerm_role_assignment.cmk_crypto_service_encryption_user : key => assignment.id }
}
