variable "subscription_id" {
  description = "Target environment subscription ID."
  type        = string

  validation {
    condition     = can(regex("^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$", var.subscription_id))
    error_message = "subscription_id must be an Azure subscription GUID."
  }
}

variable "environment" {
  description = "Environment name: dev, uat, or prd."
  type        = string

  validation {
    condition     = contains(["dev", "uat", "prd"], var.environment)
    error_message = "environment must be dev, uat, or prd."
  }
}

variable "application_resource_group_name" {
  description = "Existing application resource group containing the CMK identities."
  type        = string
}

variable "key_vault_name" {
  description = "Existing Key Vault containing the customer-managed key."
  type        = string
}

variable "key_vault_resource_group_name" {
  description = "Existing resource group containing the Key Vault."
  type        = string
}

variable "cmk_identities" {
  description = "CMK user-assigned managed identities that receive key wrap and unwrap permissions."
  type = map(object({
    name = string
  }))

  validation {
    condition = toset(keys(var.cmk_identities)) == toset([
      "cmk-document-intelligence",
      "cmk-foundry",
      "cmk-postgresql",
      "cmk-servicebus",
      "cmk-storage",
    ])
    error_message = "cmk_identities must define exactly the five CMK identity keys used by Core."
  }
}
