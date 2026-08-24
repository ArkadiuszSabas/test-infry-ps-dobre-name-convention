output "managed_identity_principal_ids" {
  value       = module.managed_identities.principal_ids
  description = "Workload principals consumed by the RBAC root."
}

output "service_principal_ids" {
  description = "System-assigned principals consumed by the RBAC phase."
  value = {
    document_intelligence = module.ai_services.document_intelligence_principal_id
  }
}

output "container_apps_environment_default_domain" {
  value       = module.container_apps.environment_default_domain
  description = "Container Apps Environment default domain consumed by the network root when it creates private DNS records."
}

output "private_endpoint_targets" {
  description = "Core resource IDs consumed by the network completion pass."
  value = {
    key_vault             = module.key_vault.id
    storage_blob          = module.storage.id
    service_bus           = azurerm_servicebus_namespace.this.id
    postgresql            = module.postgresql.id
    document_intelligence = module.ai_services.document_intelligence_id
    foundry               = module.ai_services.foundry_account_id
    azure_monitor         = module.observability.monitor_private_link_scope_id
    container_apps        = module.container_apps.environment_id
  }
}

output "rbac_scopes" {
  description = "Resource scopes consumed by the RBAC root."
  value = {
    resource_group        = data.azurerm_resource_group.environment.id
    key_vault             = module.key_vault.id
    storage               = module.storage.id
    container_registry    = module.container_registry.id
    service_bus           = azurerm_servicebus_namespace.this.id
    document_intelligence = module.ai_services.document_intelligence_id
    foundry               = module.ai_services.foundry_account_id
    service_bus_queues    = { for key, queue in azurerm_servicebus_queue.this : key => queue.id }
    storage_containers = {
      for name in module.storage.container_names :
      name => "${module.storage.id}/blobServices/default/containers/${name}"
    }
  }
}

output "runtime_configuration" {
  description = "Non-secret endpoints and names copied into the cumulative runtime tfvars file."
  value = {
    application_insights_connection_string = module.observability.application_insights_connection_string
    container_registry_login_server        = module.container_registry.login_server
    document_intelligence_endpoint         = module.ai_services.document_intelligence_endpoint
    foundry_endpoint                       = module.ai_services.foundry_endpoint
    foundry_project_name                   = module.ai_services.foundry_project_name
    gpt_deployment_name                    = module.ai_services.gpt_deployment_name
    gpt_model_name                         = module.ai_services.gpt_model_name
    postgresql_fqdn                        = module.postgresql.fqdn
    service_bus_fully_qualified_namespace  = "${azurerm_servicebus_namespace.this.name}.servicebus.windows.net"
    storage_blob_endpoint                  = module.storage.primary_blob_endpoint
  }
}
