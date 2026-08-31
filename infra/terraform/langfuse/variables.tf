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

variable "location" {
  description = "Azure region containing the ProService DEV platform."
  type        = string
  default     = "swedencentral"
}

variable "application_resource_group_name" {
  description = "Existing ProService DEV resource group containing the application platform."
  type        = string
}

variable "network_resource_group_name" {
  description = "Existing ProService DEV resource group containing the VNet and Private Endpoint subnet."
  type        = string
}

variable "private_dns_resource_group_name" {
  description = "Existing hub resource group containing the shared Private DNS Zones."
  type        = string
}

variable "private_dns_subscription_id" {
  description = "Hub subscription ID containing the shared Private DNS Zones."
  type        = string

  validation {
    condition     = can(regex("^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$", var.private_dns_subscription_id))
    error_message = "private_dns_subscription_id must be an Azure subscription GUID."
  }
}

variable "resource_names" {
  description = "Approved names for shared platform resources and Langfuse-owned resources."
  type = object({
    container_apps_environment     = string
    container_registry             = string
    key_vault                      = string
    virtual_network                = string
    private_endpoint_subnet        = string
    storage_blob_private_dns_zone  = string
    storage_file_private_dns_zone  = string
    langfuse_storage_account       = string
    langfuse_files_storage_account = string
    langfuse_web                   = string
    langfuse_worker                = string
    langfuse_clickhouse            = string
    langfuse_postgres              = string
    langfuse_valkey                = string
  })
}

variable "workload_identity_names" {
  description = "Approved managed identity names for the five Langfuse workloads."
  type = object({
    web        = string
    worker     = string
    clickhouse = string
    postgres   = string
    valkey     = string
  })
}

variable "llmmagic_identity_name" {
  description = "Existing LLM Magic identity receiving access to the Langfuse project API keys."
  type        = string
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
    init_project_public_key = "langfuse-public-key"
    init_project_secret_key = "langfuse-secret-key"
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
