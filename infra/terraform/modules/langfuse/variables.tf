variable "enabled" {
  description = "Whether the Langfuse ACA stack is provisioned."
  type        = bool
}

variable "location" {
  description = "Azure region for Langfuse resources."
  type        = string
}

variable "environment" {
  description = "Deployment environment label used for Langfuse project initialization."
  type        = string
}

variable "private_access_enabled" {
  description = "Whether the shared Container Apps Environment is behind the approved VPN/private-ingress cutoff."
  type        = bool
}

variable "resource_group_name" {
  description = "Resource group containing the shared Container Apps Environment."
  type        = string
}

variable "container_app_environment_id" {
  description = "Shared Container Apps Environment resource ID."
  type        = string
}

variable "container_app_environment_default_domain" {
  description = "Default domain of the shared Container Apps Environment."
  type        = string
}

variable "registry_server" {
  description = "ACR login server containing mirrored Langfuse, ClickHouse, PostgreSQL, and Valkey images."
  type        = string
}

variable "storage_account_name" {
  description = "Dedicated storage account name for Langfuse event and media blobs."
  type        = string
}

variable "clickhouse_storage_account_name" {
  description = "Dedicated Premium Azure Files account name for stateful Langfuse NFS volumes."
  type        = string
}

variable "private_endpoint_subnet_id" {
  description = "Subnet used for the Langfuse Blob and ClickHouse File private endpoints."
  type        = string
}

variable "storage_blob_private_dns_zone_id" {
  description = "Private DNS zone ID for Azure Blob Storage."
  type        = string
}

variable "storage_file_private_dns_zone_id" {
  description = "Private DNS zone ID for Azure Files."
  type        = string
}

variable "key_vault_uri" {
  description = "Versionless Key Vault URI containing Langfuse application secrets."
  type        = string
}

variable "secret_names" {
  description = "Key Vault secret names required by the Langfuse stack."
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
}

variable "workloads" {
  description = "Names, images, and managed identities for Langfuse workloads."
  type = object({
    web = object({
      name               = string
      image              = string
      identity_id        = string
      identity_client_id = string
    })
    worker = object({
      name               = string
      image              = string
      identity_id        = string
      identity_client_id = string
    })
    clickhouse = object({
      name               = string
      image              = string
      identity_id        = string
      identity_client_id = string
    })
    postgres = object({
      name               = string
      image              = string
      identity_id        = string
      identity_client_id = string
    })
    valkey = object({
      name               = string
      image              = string
      identity_id        = string
      identity_client_id = string
    })
  })
}

variable "clickhouse_cpu" {
  description = "CPU allocated to the single ClickHouse DEV replica."
  type        = number
  default     = 4
}

variable "clickhouse_memory" {
  description = "Memory allocated to the single ClickHouse DEV replica."
  type        = string
  default     = "16Gi"
}

variable "clickhouse_workload_profile_name" {
  description = "Dedicated ACA workload profile assigned to ClickHouse."
  type        = string

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{1,15}$", var.clickhouse_workload_profile_name))
    error_message = "ClickHouse workload profile name must be a lowercase ACA profile name between 2 and 16 characters."
  }
}

variable "web_cpu" {
  description = "CPU allocated to each Langfuse Web replica."
  type        = number
  default     = 2
}

variable "web_memory" {
  description = "Memory allocated to each Langfuse Web replica."
  type        = string
  default     = "4Gi"
}

variable "worker_cpu" {
  description = "CPU allocated to each Langfuse Worker replica."
  type        = number
  default     = 2
}

variable "worker_memory" {
  description = "Memory allocated to each Langfuse Worker replica."
  type        = string
  default     = "4Gi"
}

variable "node_options" {
  description = "Node.js runtime options shared by Langfuse Web and Worker."
  type        = string
  default     = "--max-old-space-size=3072"
}

variable "web_http_concurrent_requests" {
  description = "Concurrent HTTP requests per Langfuse Web replica before ACA scales out."
  type        = number
  default     = 10

  validation {
    condition     = var.web_http_concurrent_requests >= 1
    error_message = "Langfuse Web HTTP concurrency threshold must be at least 1."
  }
}

variable "worker_cpu_scale_threshold" {
  description = "Average worker CPU utilization percentage before ACA scales out."
  type        = number
  default     = 50

  validation {
    condition     = var.worker_cpu_scale_threshold >= 1 && var.worker_cpu_scale_threshold <= 100
    error_message = "Langfuse Worker CPU scale threshold must be between 1 and 100."
  }
}

variable "clickhouse_share_quota_gb" {
  description = "Premium Azure Files NFS quota for ClickHouse data."
  type        = number
  default     = 100

  validation {
    condition     = var.clickhouse_share_quota_gb >= 100
    error_message = "ClickHouse Premium Azure Files NFS quota must be at least 100 GiB."
  }
}

variable "postgres_share_quota_gb" {
  description = "Premium Azure Files NFS quota for PostgreSQL data."
  type        = number
  default     = 100

  validation {
    condition     = var.postgres_share_quota_gb >= 100
    error_message = "PostgreSQL Premium Azure Files NFS quota must be at least 100 GiB."
  }
}

variable "postgres_cpu" {
  description = "CPU allocated to the single PostgreSQL DEV replica."
  type        = number
  default     = 2
}

variable "postgres_memory" {
  description = "Memory allocated to the single PostgreSQL DEV replica."
  type        = string
  default     = "4Gi"
}

variable "valkey_share_quota_gb" {
  description = "Premium Azure Files NFS quota for Valkey AOF data."
  type        = number
  default     = 100

  validation {
    condition     = var.valkey_share_quota_gb >= 100
    error_message = "Valkey Premium Azure Files NFS quota must be at least 100 GiB."
  }
}

variable "valkey_cpu" {
  description = "CPU allocated to the single Valkey DEV replica."
  type        = number
  default     = 1
}

variable "valkey_memory" {
  description = "Memory allocated to the single Valkey DEV replica."
  type        = string
  default     = "2Gi"
}

variable "valkey_maxmemory" {
  description = "Valkey dataset memory ceiling, leaving headroom for the process and AOF buffers."
  type        = string
  default     = "1536mb"

  validation {
    condition     = can(regex("^[1-9][0-9]*(mb|gb)$", var.valkey_maxmemory))
    error_message = "Valkey maxmemory must be a positive whole number followed by mb or gb."
  }
}

variable "event_blob_retention_days" {
  description = "Days to retain raw Langfuse event blobs used for ingestion retries and recovery."
  type        = number
  default     = 30

  validation {
    condition     = var.event_blob_retention_days >= 7
    error_message = "Langfuse event Blob retention must be at least 7 days."
  }
}

variable "tags" {
  description = "Common Azure resource tags."
  type        = map(string)
}
