variable "log_analytics_workspace_name" {
  description = "Log Analytics Workspace name."
  type        = string
}

variable "application_insights_name" {
  description = "Workspace-based Application Insights component name."
  type        = string
}

variable "monitor_private_link_scope_name" {
  description = "Azure Monitor Private Link Scope name created locally or shared from a hub environment."
  type        = string
}

variable "shared_monitor_private_link_scope_resource_group_name" {
  description = "Optional resource group of an existing shared Azure Monitor Private Link Scope. When set, this module attaches its monitoring resources without creating another scope."
  type        = string
  default     = null
  nullable    = true
}

variable "scoped_service_name_suffix" {
  description = "Optional suffix that keeps scoped-service names unique when multiple environments share one Azure Monitor Private Link Scope."
  type        = string
  default     = null
  nullable    = true

  validation {
    condition     = var.scoped_service_name_suffix == null ? true : can(regex("^[a-z0-9][a-z0-9-]*$", var.scoped_service_name_suffix))
    error_message = "Azure Monitor scoped-service suffix must use lowercase letters, digits, and hyphens."
  }
}

variable "location" {
  description = "Azure region for Log Analytics Workspace."
  type        = string
}

variable "resource_group_name" {
  description = "Resource group where observability resources are created."
  type        = string
}

variable "retention_in_days" {
  description = "Log Analytics data retention in days."
  type        = number
}

variable "daily_quota_gb" {
  description = "Optional Log Analytics daily ingestion cap in GB."
  type        = number
  default     = null
  nullable    = true

  validation {
    condition     = var.daily_quota_gb == null ? true : var.daily_quota_gb >= 0.023
    error_message = "Log Analytics daily quota must be at least 0.023 GB when set."
  }
}

variable "tags" {
  description = "Common tags applied to observability resources."
  type        = map(string)
}
