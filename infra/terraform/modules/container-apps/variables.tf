variable "environment_name" {
  description = "Container Apps Environment name."
  type        = string
}

variable "location" {
  description = "Azure region for Container Apps resources."
  type        = string
}

variable "resource_group_name" {
  description = "Resource group where Container Apps resources are created."
  type        = string
}

variable "log_analytics_workspace_id" {
  description = "Log Analytics Workspace resource ID used by Container Apps Environment."
  type        = string
}

variable "infrastructure_subnet_id" {
  description = "Delegated subnet ID used by the Container Apps Environment."
  type        = string
}

variable "public_network_access" {
  description = "Container Apps Environment public network access mode."
  type        = string
  default     = "Enabled"

  validation {
    condition     = contains(["Disabled", "Enabled"], var.public_network_access)
    error_message = "Container Apps Environment public network access must be Disabled or Enabled."
  }
}

variable "workload_profiles" {
  description = "Additional dedicated workload profiles keyed by the profile name used by Container Apps."
  type = map(object({
    workload_profile_type = string
    minimum_count         = number
    maximum_count         = number
  }))
  default = {}

  validation {
    condition = alltrue([
      for name, profile in var.workload_profiles :
      can(regex("^[a-z0-9][a-z0-9-]{0,14}[a-z0-9]$", name)) &&
      can(regex("^[DE](4|8|16|32)$", profile.workload_profile_type)) &&
      profile.minimum_count >= 0 &&
      profile.maximum_count >= 1 &&
      profile.maximum_count >= profile.minimum_count
    ])
    error_message = "Dedicated Container Apps workload profiles require a 2-16 character lowercase name, a supported D/E profile type, and valid replica limits."
  }
}

variable "app_environment" {
  description = "Application environment name exposed to containers."
  type        = string
}

variable "registry_server" {
  description = "Container registry login server."
  type        = string
}

variable "web_public_origin" {
  description = "Public HTTPS origin used by browser clients to reach the web app. Null uses the Container Apps default web FQDN."
  type        = string
  default     = null
  nullable    = true
}

variable "web_api_proxy_upstream_timeout_ms" {
  description = "Upstream timeout in milliseconds used by the web app API proxy."
  type        = number
  default     = 30000
}

variable "scale_cooldown_period_in_seconds" {
  description = "Time without scale-trigger activity before Container Apps can scale down to the minimum replica count."
  type        = number
  default     = 300

  validation {
    condition     = var.scale_cooldown_period_in_seconds >= 1 && var.scale_cooldown_period_in_seconds <= 3600
    error_message = "Container Apps scale cooldown period must be between 1 and 3600 seconds."
  }
}

variable "apps" {
  description = "Container app definitions keyed by workload name."
  type = map(object({
    name                  = string
    container_name        = string
    image                 = string
    target_port           = number
    external_enabled      = bool
    transport             = string
    cpu                   = number
    memory                = string
    min_replicas          = number
    max_replicas          = number
    identity_id           = string
    identity_client_id    = string
    extra_identity_ids    = optional(set(string), [])
    environment_variables = map(string)
    health_probes = optional(object({
      startup = optional(object({
        path                    = string
        interval_seconds        = number
        timeout                 = number
        failure_count_threshold = number
      }))
      liveness = optional(object({
        path                    = string
        interval_seconds        = number
        timeout                 = number
        failure_count_threshold = number
      }))
      readiness = optional(object({
        path                    = string
        interval_seconds        = number
        timeout                 = number
        failure_count_threshold = number
      }))
    }), null)
    dapr = optional(object({
      app_id       = string
      app_port     = number
      app_protocol = string
    }))
    key_vault_secrets = optional(map(object({
      key_vault_secret_id = string
      identity_id         = optional(string)
    })), {})
    secret_environment_variables = optional(map(string), {})
    custom_scale_rules = optional(map(object({
      custom_rule_type = string
      metadata         = map(string)
      identity_id      = optional(string)
    })), {})
  }))
}

variable "dapr_components" {
  description = "Dapr components attached to the Container Apps Environment."
  type = map(object({
    name           = string
    component_type = string
    version        = string
    ignore_errors  = bool
    init_timeout   = string
    scopes         = set(string)
    metadata       = map(string)
  }))
  default = {}
}

variable "jobs" {
  description = "Manual Container Apps job definitions keyed by workload name."
  type = map(object({
    name                       = string
    container_name             = string
    image                      = string
    command                    = list(string)
    args                       = list(string)
    cpu                        = number
    memory                     = string
    replica_timeout_in_seconds = number
    replica_retry_limit        = number
    parallelism                = number
    replica_completion_count   = number
    identity_id                = string
    identity_client_id         = string
    registry_identity_id       = string
    environment_variables      = map(string)
    key_vault_secrets = optional(map(object({
      key_vault_secret_id = string
      identity_id         = optional(string)
    })), {})
    secret_environment_variables = optional(map(string), {})
  }))
  default = {}
}

variable "tags" {
  description = "Common tags applied to Container Apps resources."
  type        = map(string)
}
