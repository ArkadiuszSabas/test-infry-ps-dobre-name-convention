output "managed_identity_ids" {
  description = "Azure resource IDs for CMK user-assigned managed identities."
  value       = module.cmk_identities.ids
}

output "managed_identity_client_ids" {
  description = "Client IDs for CMK user-assigned managed identities."
  value       = module.cmk_identities.client_ids
}

output "managed_identity_principal_ids" {
  description = "Principal IDs consumed by the RBAC CMK role assignments."
  value       = module.cmk_identities.principal_ids
}
