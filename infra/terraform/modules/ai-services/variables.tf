variable "document_intelligence_name" {
  description = "Document Intelligence account name."
  type        = string
}

variable "document_intelligence_sku_name" {
  description = "Document Intelligence SKU name."
  type        = string
}

variable "foundry_account_name" {
  description = "Azure AI Foundry account name."
  type        = string
}

variable "foundry_enabled" {
  description = "Whether Azure AI Foundry, its project, and the GPT deployment are managed by this module."
  type        = bool
  default     = true
}

variable "foundry_cmk_enabled" {
  description = "Whether Azure AI Foundry uses a customer-managed key and its dedicated user-assigned identity."
  type        = bool
  default     = false
}

variable "foundry_sku_name" {
  description = "Azure AI Foundry account SKU name."
  type        = string
}

variable "foundry_project_name" {
  description = "Azure AI Foundry project name."
  type        = string
}

variable "foundry_project_display_name" {
  description = "Azure AI Foundry project display name."
  type        = string
}

variable "foundry_project_description" {
  description = "Azure AI Foundry project description."
  type        = string
}

variable "gpt_deployment" {
  description = "GPT model deployment configuration for Azure AI Foundry."
  type = object({
    name                       = string
    model_format               = string
    model_name                 = string
    model_version              = string
    sku_name                   = string
    capacity                   = number
    dynamic_throttling_enabled = bool
    version_upgrade_option     = string
  })
}

variable "location" {
  description = "Azure region for AI services."
  type        = string
}

variable "document_intelligence_location" {
  description = "Azure region for Document Intelligence."
  type        = string
}

variable "resource_group_name" {
  description = "Resource group where AI services are created."
  type        = string
}

variable "public_network_access_enabled" {
  description = "Whether public network access is enabled for AI services."
  type        = bool
  default     = false
}

variable "document_intelligence_public_network_access_enabled" {
  description = "Whether public network access is enabled for Document Intelligence."
  type        = bool
  default     = false
}

variable "network_acls_default_action" {
  description = "Default AI services network ACL action."
  type        = string
  default     = "Deny"

  validation {
    condition     = contains(["Allow", "Deny"], var.network_acls_default_action)
    error_message = "AI services network ACL default action must be Allow or Deny."
  }
}

variable "document_intelligence_network_acls_ip_rules" {
  description = "Static public IPv4 addresses allowed to reach Document Intelligence."
  type        = set(string)
  default     = []

  validation {
    condition = alltrue([
      for ip_rule in var.document_intelligence_network_acls_ip_rules :
      can(regex("^([0-9]{1,3}\\.){3}[0-9]{1,3}$", ip_rule)) &&
      can(cidrnetmask("${ip_rule}/32")) &&
      !can(regex("^(0\\.|10\\.|100\\.(6[4-9]|[7-9][0-9]|1[01][0-9]|12[0-7])\\.|127\\.|169\\.254\\.|172\\.(1[6-9]|2[0-9]|3[01])\\.|192\\.168\\.|192\\.0\\.(0|2)\\.|192\\.88\\.99\\.|198\\.(18|19)\\.|198\\.51\\.100\\.|203\\.0\\.113\\.|22[4-9]\\.|23[0-9]\\.|24[0-9]\\.|25[0-5]\\.)", ip_rule))
    ])
    error_message = "Document Intelligence network ACL IP rules must be valid public IPv4 addresses."
  }
}

variable "document_intelligence_user_principal_ids" {
  description = "Principal IDs granted Cognitive Services User on Document Intelligence."
  type        = map(string)
}

variable "foundry_user_principal_ids" {
  description = "Principal IDs granted Cognitive Services User on Azure AI Foundry."
  type        = map(string)
}

variable "foundry_openai_user_principal_ids" {
  description = "Principal IDs granted Cognitive Services OpenAI User on Azure AI Foundry."
  type        = map(string)
}

variable "document_intelligence_cmk_key_vault_key_id" {
  description = "Versioned Key Vault or Managed HSM key ID required to encrypt Document Intelligence."
  type        = string
}

variable "foundry_cmk_key_vault_key_id" {
  description = "Versioned Key Vault or Managed HSM key ID required to encrypt Foundry."
  type        = string
}

variable "document_intelligence_cmk_identity_id" {
  description = "User-assigned identity permitted to use the Document Intelligence CMK."
  type        = string
}

variable "document_intelligence_cmk_identity_client_id" {
  description = "Client ID of the identity permitted to use the Document Intelligence CMK."
  type        = string
}

variable "foundry_cmk_identity_id" {
  description = "User-assigned identity permitted to use the Foundry CMK."
  type        = string
}

variable "foundry_cmk_identity_client_id" {
  description = "Client ID of the identity permitted to use the Foundry CMK."
  type        = string
}

variable "tags" {
  description = "Common tags applied to AI services."
  type        = map(string)
}
