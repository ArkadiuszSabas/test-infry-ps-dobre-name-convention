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
