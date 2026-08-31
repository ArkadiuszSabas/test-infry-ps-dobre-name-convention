variable "subscription_id" {
  description = "Target ProService DEV subscription ID."
  type        = string

  validation {
    condition     = can(regex("^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$", var.subscription_id))
    error_message = "subscription_id must be an Azure subscription GUID."
  }
}

variable "environment" {
  description = "Deployment environment. The approved Langfuse ACA topology is DEV-only."
  type        = string
  default     = "dev"

  validation {
    condition     = var.environment == "dev"
    error_message = "The current Langfuse topology may be deployed only to dev."
  }
}

variable "tenant_prefix" { type = string }
variable "app_id" { type = string }
variable "instance_number" { type = string }

variable "runtime_enabled" {
  description = "False for Langfuse Core Foundation; true only after RBAC and Network Completion succeed."
  type        = bool
  default     = false
}

variable "runtime_dependencies_ready" {
  description = "Explicit confirmation that Langfuse RBAC and Private Endpoints are deployed before enabling runtime."
  type        = bool
  default     = false
}

variable "location" {
  description = "Azure region containing the ProService DEV platform."
  type        = string
  default     = "swedencentral"
}

variable "application_resource_group_name" {
  description = "Existing ProService DEV resource group containing the application platform."
  type        = string
}

variable "resource_names" {
  description = "Approved names for shared platform resources and Langfuse-owned resources."
  type = object({
    container_apps_environment = string
    container_registry         = string
    key_vault                  = string
  })
}

variable "langfuse_version" {
  description = "Pinned Langfuse Web and Worker image tag mirrored into ACR."
  type        = string
  default     = "3.185.0"
}

variable "clickhouse_version" {
  description = "Pinned ClickHouse image tag mirrored into ACR."
  type        = string
  default     = "25.11"
}

variable "postgres_version" {
  description = "Pinned PostgreSQL image tag mirrored into ACR."
  type        = string
  default     = "16.14-alpine"
}

variable "valkey_version" {
  description = "Pinned Valkey image tag mirrored into ACR."
  type        = string
  default     = "8.1.8-alpine"
}

variable "secret_names" {
  description = "Existing Key Vault secret names required by Langfuse."
  type = object({
    clickhouse_password     = string
    encryption_key          = string
    init_project_public_key = string
    init_project_secret_key = string
    nextauth_secret         = string
    postgres_password       = string
    salt                    = string
    valkey_password         = string
  })
  default = {
    clickhouse_password     = "langfuse-clickhouse-password"
    encryption_key          = "langfuse-encryption-key"
    init_project_public_key = "langfuse-init-public-key"
    init_project_secret_key = "langfuse-init-secret-key"
    nextauth_secret         = "langfuse-nextauth-secret"
    postgres_password       = "langfuse-postgres-password"
    salt                    = "langfuse-salt"
    valkey_password         = "langfuse-valkey-password"
  }
}

variable "tags" {
  description = "Common Azure resource tags."
  type        = map(string)
}
