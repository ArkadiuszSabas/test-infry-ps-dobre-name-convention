subscription_id                 = "16060ea2-28be-4b09-8e6d-060249d69ddd"
location                        = "swedencentral"
environment                     = "dev"
tenant_prefix                   = "ee7c45"
app_id                          = "ocr"
instance_number                 = "01"
application_resource_group_name = "rg-ocr-dev-arksab"
network_resource_group_name     = "rg-ocr-dev-net-arksab"

cmk = {
  storage_key_id               = "https://kv-ocr-dev-cmk-arksab.vault.azure.net/keys/cmk2048/07853f7aa77c47f4a9149a9aab90110a"
  document_intelligence_key_id = "https://kv-ocr-dev-cmk-arksab.vault.azure.net/keys/cmk2048/07853f7aa77c47f4a9149a9aab90110a"
  postgresql_key_id            = "https://kv-ocr-dev-cmk-arksab.vault.azure.net/keys/cmk2048/07853f7aa77c47f4a9149a9aab90110a"
}

# Existing network objects read directly by Core.
virtual_network_name                      = "vnet-ocr-dev-arksab"
container_apps_infrastructure_subnet_name = "snet-ocr-dev-aca-arksab"

# Set true only after the matching ProService decisions are formally approved.
security_design_approved        = true
resource_provider_list_verified = true
runtime_dependencies_ready      = false
foundry_enabled                 = true

# Confirm global availability and replace the explicit tokens before planning.
workload_identity_workloads = ["web", "api", "api-migrator", "dapr-servicebus-api", "dapr-servicebus-worker", "llmmagic", "worker"]

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
  application = "ocr"
  customer    = "proservice"
  environment = "dev"
  managed_by  = "terraform"
}
