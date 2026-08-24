subscription_id                 = "fe31d3c8-576f-4c09-913c-635306834ff0"
location                        = "swedencentral"
environment                     = "dev"
tenant_prefix                   = "ee7c45"
app_id                          = "ocr"
instance_number                 = "01"
application_resource_group_name = "rg-ocr-dev"
network_resource_group_name     = "rg-ocr-dev-net"

# Existing network objects read directly by Core.
virtual_network_name                      = "vnet-ocr-dev"
container_apps_infrastructure_subnet_name = "snet-ocr-dev-aca"
cmk = {
  storage_key_id               = "https://ee7c45-kv-ocr-dev-01.vault.azure.net/keys/cmk-ocr-dev-storage-01/d9e421f1bc034958aa5989d2137d3402"
  document_intelligence_key_id = "https://ee7c45-kv-ocr-dev-01.vault.azure.net/keys/cmk-ocr-dev-docint-01/373716851d784358b4f05336c5833c36"
  postgresql_key_id            = "https://ee7c45-kv-ocr-dev-01.vault.azure.net/keys/cmk-ocr-dev-postgres-01/d87d4fbc26ab4918ba531bffc80b29f6"
}

# Set true only after the matching ProService decisions are formally approved.
security_design_approved        = false
resource_provider_list_verified = false
runtime_dependencies_ready      = false # for core-foundation set it to 'false'
foundry_enabled                 = true

workload_identity_workloads = [
  "web",
  "api",
  "api-migrator",
  "dapr-servicebus-api",
  "dapr-servicebus-worker",
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
  sku_name                   = "GlobalStandard"
  capacity                   = 1000
  dynamic_throttling_enabled = false
  version_upgrade_option     = "NoAutoUpgrade"
}

container_apps     = {}
dapr_components    = {}
container_app_jobs = {}

tags = {
  application  = "ocr"
  environment  = "dev"
  managed_by   = "terraform"
  organization = "psf"
}
