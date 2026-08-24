variable "name" {
  description = "Storage Account name."
  type        = string
}

variable "location" {
  description = "Azure region for Storage Account."
  type        = string
}

variable "resource_group_name" {
  description = "Resource group where Storage Account is created."
  type        = string
}

variable "replication_type" {
  description = "Storage Account replication type, for example LRS or GRS."
  type        = string
}

variable "containers" {
  description = "Private blob containers to create."
  type        = set(string)
}

variable "blob_data_contributor_assignments" {
  description = "Storage Blob Data Contributor grants by workload, scoped to specific containers."
  type = map(object({
    principal_id                     = string
    principal_type                   = optional(string)
    container_names                  = set(string)
    skip_service_principal_aad_check = optional(bool, true)
  }))

  validation {
    condition = alltrue([
      for assignment in values(var.blob_data_contributor_assignments) :
      assignment.principal_type == null || contains(["User", "Group", "ServicePrincipal"], assignment.principal_type)
    ])
    error_message = "Storage Blob Data Contributor principal type must be User, Group, ServicePrincipal, or null."
  }
}

variable "shared_access_key_enabled" {
  description = "Whether Storage Account shared key access is enabled."
  type        = bool
}

variable "default_to_oauth_authentication" {
  description = "Whether Azure portal defaults to OAuth authentication for data operations."
  type        = bool
}

variable "public_network_access_enabled" {
  description = "Whether public network access is enabled for the Storage Account."
  type        = bool
  default     = false
}

variable "cmk_key_vault_key_id" {
  description = "Versioned Key Vault or Managed HSM key ID used to encrypt the storage account."
  type        = string
}

variable "cmk_user_assigned_identity_id" {
  description = "User-assigned identity permitted to use the storage CMK."
  type        = string
}

variable "tags" {
  description = "Common tags applied to Storage Account."
  type        = map(string)
}
