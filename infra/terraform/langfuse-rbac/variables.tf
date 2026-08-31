variable "subscription_id" { type = string }
variable "environment" { type = string }
variable "app_id" { type = string }
variable "instance_number" { type = string }
variable "application_resource_group_name" { type = string }
variable "container_registry_name" { type = string }
variable "key_vault_name" { type = string }
variable "llmmagic_identity_name" { type = string }
variable "secret_names" {
  type = object({ clickhouse_password = string, encryption_key = string, init_project_public_key = string, init_project_secret_key = string, nextauth_secret = string, postgres_password = string, salt = string, valkey_password = string })
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
