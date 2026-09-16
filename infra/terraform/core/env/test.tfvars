subscription_id                 = "ade38c32-9ade-4049-a9e1-bce6d1692438"
location                        = "swedencentral"
environment                     = "test"
tenant_prefix                   = "ee7c45"
app_id                          = "ocr"
instance_number                 = "01"
application_resource_group_name = "rg-ocr-test"
network_resource_group_name     = "rg-ocr-test-net"

# Existing network objects read directly by Core.
virtual_network_name                      = "vnet-ocr-test"
container_apps_infrastructure_subnet_name = "snet-ocr-test-aca"
cmk = {
  storage_key_id               = "https://ee7c45-kv-ocr-test-01.vault.azure.net/keys/cmk-ocr-test-storage-01/ecc0ed5e87a04b7f9dcceee01c54e957"
  document_intelligence_key_id = "https://ee7c45-kv-ocr-test-01.vault.azure.net/keys/cmk-ocr-test-docint-01/8a316bf0e0fc4f0b9c955b92568d6e03"
  postgresql_key_id            = "https://ee7c45-kv-ocr-test-01.vault.azure.net/keys/cmk-ocr-test-postgres-01/a764a80f836c4753b749c797523f5ea8"
}

# Set true only after the matching ProService decisions are formally approved.
security_design_approved        = true
resource_provider_list_verified = true
runtime_dependencies_ready      = false # for core-foundation set it to 'false'
foundry_enabled                 = true
langfuse_tracing = {
  # Runtime tracing is enabled only in phase 07, after Langfuse Core is deployed.
  enabled = false
}

workload_identity_workloads = [
  "web",
  "api",
  "api-migrator",
  "dapr-servicebus-api",
  "dapr-servicebus-worker",
  "dapr-servicebus-llmmagic",
  "llmmagic",
  "worker",
]

storage_containers = [
  "archive",
  "inbox",
  "ocr-artifacts",
  "preprocessed",
  "previews",
  "quarantine",
]

gpt_deployment = {
  model_format               = "OpenAI"
  model_name                 = "gpt-5.5"
  model_version              = "2026-04-24"
  sku_name                   = "DataZoneStandard"
  capacity                   = 3000
  dynamic_throttling_enabled = false
  version_upgrade_option     = "NoAutoUpgrade"
}

container_apps     = {}
dapr_components    = {}
container_app_jobs = {}

tags = {
  application  = "ocr"
  environment  = "test"
  managed_by   = "terraform"
  organization = "psf"
}
