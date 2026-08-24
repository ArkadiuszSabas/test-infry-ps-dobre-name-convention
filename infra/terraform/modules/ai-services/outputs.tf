output "document_intelligence_id" {
  description = "Document Intelligence account resource ID."
  value       = azurerm_cognitive_account.document_intelligence.id
}

output "document_intelligence_name" {
  description = "Document Intelligence account name."
  value       = azurerm_cognitive_account.document_intelligence.name
}

output "document_intelligence_endpoint" {
  description = "Document Intelligence endpoint."
  value       = azurerm_cognitive_account.document_intelligence.endpoint
}

output "document_intelligence_principal_id" {
  description = "Document Intelligence system-assigned managed identity principal ID."
  value       = azurerm_cognitive_account.document_intelligence.identity[0].principal_id
}

output "foundry_account_id" {
  description = "Azure AI Foundry account resource ID."
  value       = var.foundry_enabled ? azurerm_cognitive_account.foundry[0].id : null
}

output "foundry_account_name" {
  description = "Azure AI Foundry account name."
  value       = var.foundry_enabled ? azurerm_cognitive_account.foundry[0].name : null
}

output "foundry_endpoint" {
  description = "Azure AI Foundry account endpoint."
  value       = var.foundry_enabled ? azurerm_cognitive_account.foundry[0].endpoint : null
}

output "foundry_project_id" {
  description = "Azure AI Foundry project resource ID."
  value       = var.foundry_enabled ? azurerm_cognitive_account_project.foundry[0].id : null
}

output "foundry_project_name" {
  description = "Azure AI Foundry project name."
  value       = var.foundry_enabled ? azurerm_cognitive_account_project.foundry[0].name : null
}

output "gpt_deployment_name" {
  description = "Configured GPT deployment name."
  value       = var.foundry_enabled ? var.gpt_deployment.name : null
}

output "gpt_model_name" {
  description = "GPT model name."
  value       = var.foundry_enabled ? var.gpt_deployment.model_name : null
}

output "gpt_model_version" {
  description = "GPT model version."
  value       = var.foundry_enabled ? var.gpt_deployment.model_version : null
}
