output "environment_id" {
  description = "Container Apps Environment resource ID."
  value       = azurerm_container_app_environment.this.id
}

output "environment_name" {
  description = "Container Apps Environment name."
  value       = azurerm_container_app_environment.this.name
}

output "environment_default_domain" {
  description = "Container Apps Environment default domain."
  value       = azurerm_container_app_environment.this.default_domain
}

output "container_app_names" {
  description = "Container App names keyed by workload name."
  value       = { for key, app in azurerm_container_app.this : key => app.name }
}

output "container_app_latest_revision_fqdns" {
  description = "Latest revision FQDNs keyed by workload name."
  value       = { for key, app in azurerm_container_app.this : key => app.latest_revision_fqdn }
}

output "container_app_fqdns" {
  description = "Stable ingress FQDNs keyed by workload name."
  value       = { for key, origin in local.app_ingress_origins : key => trimprefix(origin, "https://") }
}

output "container_app_custom_domain_verification_ids" {
  description = "Custom-domain verification IDs keyed by workload name."
  value       = { for key, app in azurerm_container_app.this : key => app.custom_domain_verification_id }
}

output "container_app_outbound_ip_addresses" {
  description = "Distinct outbound IP addresses used by Container Apps."
  value       = toset(flatten([for app in azurerm_container_app.this : app.outbound_ip_addresses]))
}

output "container_app_job_names" {
  description = "Container Apps Job names keyed by workload name."
  value       = { for key, job in azurerm_container_app_job.this : key => job.name }
}

output "dapr_component_names" {
  description = "Dapr component names keyed by logical component name."
  value       = { for key, component in azurerm_container_app_environment_dapr_component.this : key => component.name }
}
