subscription_id                 = "16060ea2-28be-4b09-8e6d-060249d69ddd"
location                        = "swedencentral"
environment                     = "dev"
application_resource_group_name = "rg-ocr-dev-arksab"
network_resource_group_name     = "rg-ocr-dev-net-arksab"

cmk = {
  storage_key_id               = "https://kv-ocr-dev-cmk-arksab.vault.azure.net/keys/cmk2048/07853f7aa77c47f4a9149a9aab90110a"
  service_bus_key_id           = "https://kv-ocr-dev-cmk-arksab.vault.azure.net/keys/cmk2048/07853f7aa77c47f4a9149a9aab90110a"
  document_intelligence_key_id = "https://kv-ocr-dev-cmk-arksab.vault.azure.net/keys/cmk2048/07853f7aa77c47f4a9149a9aab90110a"
  foundry_key_id               = "https://kv-ocr-dev-cmk-arksab.vault.azure.net/keys/cmk2048/07853f7aa77c47f4a9149a9aab90110a"
  postgresql_key_id            = "https://kv-ocr-dev-cmk-arksab.vault.azure.net/keys/cmk2048/07853f7aa77c47f4a9149a9aab90110a"
}

# Existing network objects read directly by Core.
virtual_network_name                      = "vnet-ocr-dev-arksab"
container_apps_infrastructure_subnet_name = "snet-ocr-dev-aca-arksab"

# Set true only after the matching ProService decisions are formally approved.
security_design_approved        = false
resource_provider_list_verified = false
runtime_dependencies_ready      = false # for core-foundation set it to 'false'
foundry_enabled                 = true
foundry_cmk_enabled             = false

resource_names = {
  key_vault                  = "kv-ocr-dev"
  storage_account            = "stocrdev01"
  container_registry         = "acrocrdev01"
  log_analytics              = "law-ocr-dev"
  application_insights       = "appi-ocr-dev"
  monitor_private_link       = "ampls-ocr-dev"
  service_bus                = "sb-ocr-dev"
  document_intelligence      = "di-ocr-dev"
  foundry_account            = "ai-ocr-dev"
  foundry_project            = "aifp-ocr-dev"
  container_apps_environment = "cae-ocr-dev"
  postgresql                 = "psql-ocr-dev"
}

workload_identities = {
  web                    = { name = "id-ocr-web-dev" }
  api                    = { name = "id-ocr-api-dev" }
  api-migrator           = { name = "id-ocr-api-migrator-dev" }
  dapr-servicebus-api    = { name = "id-ocr-dapr-sb-api-dev" }
  dapr-servicebus-worker = { name = "id-ocr-dapr-sb-worker-dev" }
  llmmagic               = { name = "id-ocr-llmmagic-dev" }
  worker                 = { name = "id-ocr-worker-dev" }
}

storage_containers = [
  "archive",
  "inbox",
  "ocr-artifacts",
  "preprocessed",
  "previews",
  "quarantine",
]

service_bus_queues = {
  document-processing = {
    dead_lettering_on_message_expiration = true
    default_message_ttl                  = "P14D"
    lock_duration                        = "PT1M"
    max_delivery_count                   = 10
    max_size_in_megabytes                = 1024
  }
  processing-results = {
    dead_lettering_on_message_expiration = true
    default_message_ttl                  = "P14D"
    lock_duration                        = "PT1M"
    max_delivery_count                   = 10
    max_size_in_megabytes                = 1024
  }
}

postgresql_database_names = ["db-ocr-dev"]

gpt_deployment = {
  name                       = "gpt-5-5"
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
