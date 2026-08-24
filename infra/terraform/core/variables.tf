variable "subscription_id" {
  description = "Target environment subscription ID."
  type        = string

  validation {
    condition     = can(regex("^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$", var.subscription_id))
    error_message = "subscription_id must be an Azure subscription GUID."
  }
}

variable "location" {
  description = "Azure region."
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

variable "application_resource_group_name" {
  description = "Pre-created ProService application resource group."
  type        = string
}

variable "network_resource_group_name" {
  description = "Existing ProService resource group containing the Container Apps infrastructure subnet."
  type        = string
}

variable "cmk" {
  description = "Versioned Key Vault or Managed HSM key IDs used for customer-managed encryption."
  type = object({
    storage_key_id               = string
    service_bus_key_id           = string
    document_intelligence_key_id = string
    foundry_key_id               = string
    postgresql_key_id            = string
  })

  validation {
    condition = alltrue([
      for key_id in values(var.cmk) : can(regex("^https://[^/]+/keys/[^/]+/[^/]+$", key_id))
    ])
    error_message = "Every cmk key ID must be a versioned Key Vault or Managed HSM key URL."
  }
}

variable "security_design_approved" {
  description = "Explicit confirmation that ProService approved key management and private-access exceptions for this environment."
  type        = bool
  default     = false
}

variable "resource_provider_list_verified" {
  description = "Explicit confirmation that the authoritative Resource Provider list was registered outside this root."
  type        = bool
  default     = false
}

variable "runtime_dependencies_ready" {
  description = "Explicit confirmation that network completion and reviewed RBAC were applied before runtime workloads."
  type        = bool
  default     = false
}

variable "foundry_enabled" {
  description = "Whether Core manages Azure AI Foundry, its project, and the GPT deployment."
  type        = bool
  default     = true
}

variable "foundry_cmk_enabled" {
  description = "Whether Azure AI Foundry uses the external customer-managed key."
  type        = bool
  default     = false
}

variable "virtual_network_name" {
  description = "Existing virtual network containing the Container Apps infrastructure subnet."
  type        = string
}

variable "container_apps_infrastructure_subnet_name" {
  description = "Existing subnet delegated to the Container Apps environment."
  type        = string
}

variable "resource_names" {
  description = "Approved ProService resource names."
  type = object({
    key_vault                  = string
    storage_account            = string
    container_registry         = string
    log_analytics              = string
    application_insights       = string
    monitor_private_link       = string
    service_bus                = string
    document_intelligence      = string
    foundry_account            = string
    foundry_project            = string
    container_apps_environment = string
    postgresql                 = string
  })
}

variable "workload_identities" {
  description = "Managed identity definitions keyed by workload name. Must include api-migrator."
  type = map(object({
    name = string
  }))
}

variable "storage_containers" {
  description = "Private application Blob containers."
  type        = set(string)
}

variable "service_bus_queues" {
  description = "Premium Service Bus queues."
  type = map(object({
    dead_lettering_on_message_expiration = bool
    default_message_ttl                  = string
    lock_duration                        = string
    max_delivery_count                   = number
    max_size_in_megabytes                = number
  }))
}

variable "postgresql_database_names" {
  description = "Application PostgreSQL databases."
  type        = set(string)
}

variable "gpt_deployment" {
  description = "Approved Azure AI model deployment."
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

variable "container_apps" {
  description = "Complete runtime app definitions. Identity keys resolve against workload_identities. Keep the map cumulative after workloads are introduced."
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
    identity_key          = string
    extra_identity_keys   = optional(set(string), [])
    environment_variables = map(string)
    dapr = optional(object({
      app_id       = string
      app_port     = number
      app_protocol = string
    }))
    key_vault_secrets = optional(map(object({
      key_vault_secret_id = string
      identity_key        = optional(string)
    })), {})
    secret_environment_variables = optional(map(string), {})
    custom_scale_rules = optional(map(object({
      custom_rule_type = string
      metadata         = map(string)
      identity_key     = optional(string)
    })), {})
  }))
  default = {}
}

variable "dapr_components" {
  description = "Dapr components attached to the Container Apps Environment. Runtime configuration must include servicebus-pubsub-api and servicebus-pubsub-worker."
  type = map(object({
    name                         = string
    component_type               = string
    version                      = string
    ignore_errors                = bool
    init_timeout                 = string
    scopes                       = set(string)
    metadata                     = optional(map(string), {})
    managed_identity_key         = optional(string)
    service_bus_metadata_enabled = optional(bool, false)
  }))
  default = {}

  validation {
    condition = alltrue([
      for component in values(var.dapr_components) :
      !component.service_bus_metadata_enabled || component.managed_identity_key != null
    ])
    error_message = "A Dapr component with Service Bus metadata enabled must declare managed_identity_key."
  }
}

variable "container_app_jobs" {
  description = "Manual Container Apps jobs. Runtime configuration must retain the api-migrations job."
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
    identity_key               = string
    registry_identity_key      = string
    environment_variables      = map(string)
    key_vault_secrets = optional(map(object({
      key_vault_secret_id = string
      identity_key        = optional(string)
    })), {})
    secret_environment_variables = optional(map(string), {})
  }))
  default = {}
}

variable "tags" {
  description = "Common Azure resource tags."
  type        = map(string)
}
