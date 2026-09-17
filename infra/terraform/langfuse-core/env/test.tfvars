subscription_id = "ade38c32-9ade-4049-a9e1-bce6d1692438"
location        = "swedencentral"

environment     = "test"
tenant_prefix   = "ee7c45"
app_id          = "ocr"
instance_number = "01"

application_resource_group_name = "rg-ocr-test"

resource_names = {
  container_apps_environment = "cae-ocr-test-01"
  container_registry         = "ee7c45crocrtest01"
  key_vault                  = "ee7c45kvocrapptest01"
}

# Tags approved in the Langfuse ACR repositories.
langfuse_version   = "3.185.0"
clickhouse_version = "25.11"
postgres_version   = "16.14-alpine"
valkey_version     = "8.1.8-alpine"

# Foundation phase. Change both values to true only after the Langfuse RBAC
# and Network Completion workflows have succeeded.
runtime_enabled            = false
runtime_dependencies_ready = false

tags = {
  application  = "ocr"
  environment  = "test"
  managed_by   = "terraform"
  organization = "psf"
}
