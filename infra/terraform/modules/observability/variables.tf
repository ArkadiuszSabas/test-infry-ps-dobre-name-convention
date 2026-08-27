variable "log_analytics_workspace_name" {
  description = "Log Analytics Workspace name."
  type        = string
}

variable "application_insights_name" {
  description = "Workspace-based Application Insights component name."
  type        = string
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
