output "web_fqdn" {
  description = "Private Langfuse Web FQDN."
  value       = module.langfuse.web_fqdn
}

output "web_id" {
  description = "Resource ID of the private Langfuse Web Container App."
  value       = module.langfuse.web_id
}

output "container_app_names" {
  description = "Langfuse Container App names keyed by workload."
  value       = module.langfuse.container_app_names
}

output "workload_identity_ids" {
  description = "Langfuse workload managed identity resource IDs, created by Core Foundation."
  value       = module.managed_identities.ids
}

output "workload_identity_principal_ids" {
  description = "Langfuse workload managed identity principal IDs, consumed by the RBAC stage."
  value       = module.managed_identities.principal_ids
}

output "storage_account_ids" {
  description = "Langfuse storage resource IDs, consumed by Network Completion."
  value = {
    blob  = module.langfuse.storage_account_id
    files = module.langfuse.clickhouse_storage_account_id
  }
}
