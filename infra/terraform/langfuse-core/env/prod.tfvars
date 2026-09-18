subscription_id = "832f8765-ba78-4d5b-8330-e8edd672152f"
location        = "swedencentral"

environment     = "prod"
tenant_prefix   = "ee7c45"
app_id          = "ocr"
instance_number = "01"

application_resource_group_name = "rg-ocr-prod"

resource_names = {
  container_apps_environment = "cae-ocr-prod-01"
  container_registry         = "ee7c45crocrprod01"
  key_vault                  = "ee7c45kvocrappprod01"
}

# Tags approved in the Langfuse ACR repositories.
langfuse_version   = "3.185.0"
clickhouse_version = "25.11"
postgres_version   = "16.14-alpine"
valkey_version     = "8.1.8-alpine"

# Foundation phase. Enable runtime only after Langfuse RBAC, the two Langfuse
# Private Endpoints, and the eight Key Vault secrets have been created.
runtime_enabled            = false
runtime_dependencies_ready = false

tags = {
  application  = "ocr"
  environment  = "prod"
  managed_by   = "terraform"
  organization = "psf"
}
