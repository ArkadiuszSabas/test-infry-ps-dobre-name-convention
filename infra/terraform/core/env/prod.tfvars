subscription_id                 = "832f8765-ba78-4d5b-8330-e8edd672152f"
location                        = "swedencentral"
environment                     = "prod"
tenant_prefix                   = "ee7c45"
app_id                          = "ocr"
instance_number                 = "01"
application_resource_group_name = "rg-ocr-prod"
network_resource_group_name     = "rg-ocr-prod-net"

# Existing network objects read directly by Core.
virtual_network_name                      = "vnet-ocr-prod"
container_apps_infrastructure_subnet_name = "snet-ocr-prod-aca"
cmk = {
  storage_key_id               = "https://ee7c45-kv-ocr-prod-01.vault.azure.net/keys/cmk-ocr-prod-storage-01/1dc35600ac174a2d84ef3430acb4411f"
  document_intelligence_key_id = "https://ee7c45-kv-ocr-prod-01.vault.azure.net/keys/cmk-ocr-prod-docint-01/593f349d2c7a491cb2c4c0809c8eb581"
  postgresql_key_id            = "https://ee7c45-kv-ocr-prod-01.vault.azure.net/keys/cmk-ocr-prod-postgres-01/4785c8aabd6d400889aca2c52d1a18c9"
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
  environment  = "prod"
  managed_by   = "terraform"
  organization = "psf"
}
