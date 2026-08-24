output "web_fqdn" {
  description = "Private Langfuse web FQDN exposed through the private Container Apps Environment."
  value       = try(azurerm_container_app.web[0].ingress[0].fqdn, null)
}

output "web_id" {
  description = "Resource ID of the private Langfuse Web Container App."
  value       = try(azurerm_container_app.web[0].id, null)
}

output "container_app_names" {
  description = "Langfuse Container App names keyed by workload."
  value = var.enabled ? {
    web        = var.workloads.web.name
    worker     = var.workloads.worker.name
    clickhouse = var.workloads.clickhouse.name
    postgres   = var.workloads.postgres.name
    valkey     = var.workloads.valkey.name
  } : {}
}

output "storage_account_id" {
  description = "Dedicated Langfuse Blob storage account resource ID."
  value       = try(azurerm_storage_account.this[0].id, null)
}

output "clickhouse_storage_account_id" {
  description = "Dedicated stateful Langfuse Premium Azure Files storage account resource ID."
  value       = try(azurerm_storage_account.clickhouse[0].id, null)
}
