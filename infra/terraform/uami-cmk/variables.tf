variable "subscription_id" {
  description = "Target environment subscription ID."
  type        = string

  validation {
    condition     = can(regex("^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$", var.subscription_id))
    error_message = "subscription_id must be an Azure subscription GUID."
  }
}

variable "location" {
  description = "Azure region for CMK user-assigned managed identities."
  type        = string
  default     = "swedencentral"
}

variable "environment" {
  description = "Environment name: dev, uat, or prd."
  type        = string

  validation {
    condition     = contains(["dev", "uat", "prd"], var.environment)
    error_message = "environment must be dev, uat, or prd."
  }
}

variable "app_id" {
  description = "Application identifier used in managed identity names."
  type        = string
}

variable "instance_number" {
  description = "Application instance identifier used in managed identity names."
  type        = string
}

variable "application_resource_group_name" {
  description = "Existing application resource group where the CMK identities are created."
  type        = string
}

variable "cmk_identity_workloads" {
  description = "CMK workloads for which user-assigned managed identities are created."
  type        = set(string)

  validation {
    condition = var.cmk_identity_workloads == toset([
      "cmk-document-intelligence",
      "cmk-postgresql",
      "cmk-storage",
    ])
    error_message = "cmk_identity_workloads must define exactly the three CMK workloads used by Core."
  }
}

variable "tags" {
  description = "Common tags applied to CMK user-assigned managed identities."
  type        = map(string)
}
