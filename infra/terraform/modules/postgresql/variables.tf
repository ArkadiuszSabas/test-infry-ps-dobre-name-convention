variable "name" {
  description = "PostgreSQL Flexible Server name."
  type        = string
}

variable "location" {
  description = "Azure region for PostgreSQL Flexible Server."
  type        = string
}

variable "resource_group_name" {
  description = "Resource group where PostgreSQL resources are created."
  type        = string
}

variable "tenant_id" {
  description = "Microsoft Entra tenant ID used for PostgreSQL authentication."
  type        = string
}

variable "postgresql_version" {
  description = "PostgreSQL engine version."
  type        = string
}

variable "sku_name" {
  description = "PostgreSQL Flexible Server SKU name."
  type        = string
}

variable "zone" {
  description = "Availability zone for PostgreSQL Flexible Server."
  type        = string
}

variable "storage_mb" {
  description = "PostgreSQL storage size in MB."
  type        = number
}

variable "backup_retention_days" {
  description = "Backup retention in days."
  type        = number
}

variable "geo_redundant_backup_enabled" {
  description = "Whether geo-redundant backup is enabled."
  type        = bool
}

variable "database_names" {
  description = "Application database names to create."
  type        = set(string)
}

variable "firewall_ip_addresses" {
  description = "Static public IPv4 addresses allowed to connect to PostgreSQL."
  type        = set(string)
  default     = []
}

variable "public_network_access_enabled" {
  description = "Whether public network access is enabled for PostgreSQL Flexible Server."
  type        = bool
  default     = false
}

variable "cmk_key_vault_key_id" {
  description = "Versioned Key Vault or Managed HSM key ID used to encrypt PostgreSQL data."
  type        = string
}

variable "cmk_user_assigned_identity_id" {
  description = "User-assigned identity permitted to use the PostgreSQL CMK."
  type        = string
}

variable "active_directory_administrator" {
  description = "Microsoft Entra administrator for PostgreSQL."
  type = object({
    object_id      = string
    principal_name = string
    principal_type = string
  })
}

variable "tags" {
  description = "Common tags applied to PostgreSQL resources."
  type        = map(string)
}
