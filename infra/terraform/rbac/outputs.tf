output "role_assignment_ids" {
  value       = { for key, assignment in azurerm_role_assignment.this : key => assignment.id }
  description = "Created role assignment IDs keyed by reviewed logical name."
}

output "workload_identity_principal_ids" {
  value       = { for key, identity in data.azurerm_user_assigned_identity.workload : key => identity.principal_id }
  description = "Workload UAI principal IDs resolved by the RBAC phase."
}
