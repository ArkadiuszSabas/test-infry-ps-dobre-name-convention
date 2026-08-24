variable "name" {
  description = "Key Vault name."
  type        = string
}

variable "location" {
  description = "Azure region for Key Vault."
  type        = string
}

variable "resource_group_name" {
  description = "Resource group where Key Vault is created."
  type        = string
}

variable "tenant_id" {
  description = "Entra tenant ID for Key Vault."
  type        = string
}

variable "secrets_user_principal_ids" {
  description = "Principal IDs granted Key Vault Secrets User."
  type        = map(string)
}

variable "secrets_officer_principal_ids" {
  description = "Principal IDs granted Key Vault Secrets Officer for controlled secret bootstrap flows."
  type        = map(string)
  default     = {}
}

variable "secrets_officer_skip_service_principal_aad_check_by_principal" {
  description = "Per-principal override for skipping the service principal AAD check on Key Vault Secrets Officer role assignments."
  type        = map(bool)
  default     = {}
}

variable "secrets_officer_principal_types" {
  description = "Optional per-principal type used for Key Vault Secrets Officer role assignments."
  type        = map(string)
  default     = {}

  validation {
    condition = alltrue([
      for principal_type in values(var.secrets_officer_principal_types) :
      contains(["User", "Group", "ServicePrincipal"], principal_type)
    ])
    error_message = "Each Key Vault Secrets Officer principal type must be User, Group, or ServicePrincipal."
  }
}

variable "secrets_officer_principal_type" {
  description = "Optional principal type used for Key Vault Secrets Officer role assignments."
  type        = string
  default     = null
  nullable    = true

  validation {
    condition     = var.secrets_officer_principal_type == null || contains(["User", "Group", "ServicePrincipal"], var.secrets_officer_principal_type)
    error_message = "Key Vault Secrets Officer principal type must be User, Group, ServicePrincipal, or null."
  }
}

variable "public_network_access_enabled" {
  description = "Whether public network access is enabled for Key Vault."
  type        = bool
  default     = false
}

variable "network_acls_default_action" {
  description = "Default Key Vault network ACL action."
  type        = string
  default     = "Deny"

  validation {
    condition     = contains(["Allow", "Deny"], var.network_acls_default_action)
    error_message = "Key Vault network ACL default action must be Allow or Deny."
  }
}

variable "network_acls_bypass" {
  description = "Trusted service bypass mode for Key Vault network ACLs."
  type        = string
  default     = "AzureServices"

  validation {
    condition     = contains(["AzureServices", "None"], var.network_acls_bypass)
    error_message = "Key Vault network ACL bypass must be AzureServices or None."
  }
}

variable "purge_protection_enabled" {
  description = "Whether purge protection is enabled for Key Vault."
  type        = bool
  default     = false
}

variable "soft_delete_retention_days" {
  description = "Soft-delete retention period for Key Vault."
  type        = number
  default     = 7

  validation {
    condition     = var.soft_delete_retention_days >= 7 && var.soft_delete_retention_days <= 90
    error_message = "Key Vault soft-delete retention must be between 7 and 90 days."
  }
}

variable "tags" {
  description = "Common tags applied to Key Vault."
  type        = map(string)
}
