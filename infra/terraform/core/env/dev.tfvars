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
  service_bus_key_id           = "https://kv-ocr-dev-cmk-arksab.vault.azure.net/keys/cmk2048/07853f7aa77c47f4a9149a9aab90110a"
  document_intelligence_key_id = "https://kv-ocr-dev-cmk-arksab.vault.azure.net/keys/cmk2048/07853f7aa77c47f4a9149a9aab90110a"
  foundry_key_id               = "https://kv-ocr-dev-cmk-arksab.vault.azure.net/keys/cmk2048/07853f7aa77c47f4a9149a9aab90110a"
  postgresql_key_id            = "https://kv-ocr-dev-cmk-arksab.vault.azure.net/keys/cmk2048/07853f7aa77c47f4a9149a9aab90110a"
}

virtual_network_name                      = "vnet-ocr-dev-arksab"
container_apps_infrastructure_subnet_name = "snet-ocr-dev-aca-arksab"

security_design_approved        = true
resource_provider_list_verified = true
runtime_dependencies_ready      = true
foundry_enabled                 = true
foundry_cmk_enabled             = false

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

# Immutable image references from application-image-manifest.json for commit
# dd6db8823c197072c15c5d75d0d50b0f23a05b4b.
container_apps = {
  web = {
    name                  = "ca-ocr-web-dev"
    container_name        = "web"
    image                 = "acrocrdevarksab01.azurecr.io/docmind/web@sha256:fdf961371d22475a03cc7596d7c76546832fd28b5ef8c1907cc676cd24375248"
    target_port           = 3000
    external_enabled      = true
    transport             = "auto"
    cpu                   = 0.5
    memory                = "1Gi"
    min_replicas          = 1
    max_replicas          = 3
    identity_key          = "web"
    environment_variables = {}
  }
  api = {
    name                = "ca-ocr-api-dev"
    container_name      = "api"
    image               = "acrocrdevarksab01.azurecr.io/docmind/api@sha256:8615274bb9a4880920c97b28414bd8bbbdb2a8ce1a8c2d780ae365379c40f5e2"
    target_port         = 8000
    external_enabled    = true
    transport           = "auto"
    cpu                 = 1
    memory              = "2Gi"
    min_replicas        = 1
    max_replicas        = 5
    identity_key        = "api"
    extra_identity_keys = ["dapr-servicebus-api"]
    environment_variables = {
      APPLICATIONINSIGHTS_CONNECTION_STRING                  = "InstrumentationKey=c3a0b40d-62b1-4ac4-8cb2-d508b2a180fb;IngestionEndpoint=https://swedencentral-0.in.applicationinsights.azure.com/;LiveEndpoint=https://swedencentral.livediagnostics.monitor.azure.com/;ApplicationId=6c8c8884-de22-439c-bc70-2d971741af53"
      APPLICATIONINSIGHTS_STATSBEAT_DISABLED_ALL             = "true"
      DOCMIND_API_DATABASE_ECHO                              = "false"
      DOCMIND_API_DATABASE_POOL_PRE_PING                     = "true"
      DOCMIND_API_DATABASE_URL                               = "postgresql+asyncpg://id-ocr-api-dev@psql-ocr-dev-arksab.postgres.database.azure.com:5432/db-ocr-dev?ssl=require"
      DOCMIND_API_DIRECT_OCR_INVOCATION_TIMEOUT_SECONDS      = "1200"
      DOCMIND_API_DOCUMENT_STORAGE_AZURE_ACCOUNT_URL         = "https://stocrdevarksab01.blob.core.windows.net/"
      DOCMIND_API_DOCUMENT_STORAGE_AZURE_BLOB_PREFIX         = "raw"
      DOCMIND_API_DOCUMENT_STORAGE_AZURE_CONTAINER_NAME      = "inbox"
      DOCMIND_API_DOCUMENT_STORAGE_OPERATION_TIMEOUT_SECONDS = "30"
      DOCMIND_API_DOCUMENT_STORAGE_PROVIDER                  = "azure_blob"
      DOCMIND_API_LOCAL_STARTUP_MIGRATIONS_ENABLED           = "false"
      DOCMIND_AZURE_MONITOR_ENABLED                          = "true"
      DOCMIND_AZURE_MONITOR_LIVE_METRICS_ENABLED             = "false"
      DOCMIND_AZURE_MONITOR_OFFLINE_STORAGE_ENABLED          = "false"
      DOCMIND_CONNECTOR_PROFILE_ID                           = "ps"
      DOCMIND_CONNECTOR_PROFILE_PATH                         = "/app/deployments/ps/profile.yml"
      DOCMIND_DAPR_HTTP_TIMEOUT_SECONDS                      = "60.0"
      DOCMIND_DAPR_RUNTIME_HOST                              = "127.0.0.1"
      OTEL_METRICS_EXPORTER                                  = "none"
      SERVICE_BUS_DOCUMENT_PROCESSING_QUEUE_NAME             = "document-processing"
      SERVICE_BUS_FULLY_QUALIFIED_NAMESPACE                  = "sb-ocr-dev-arksab.servicebus.windows.net"
      SERVICE_BUS_PROCESSING_RESULTS_QUEUE_NAME              = "processing-results"
      STORAGE_ACCOUNT_NAME                                   = "stocrdevarksab01"
      STORAGE_BLOB_ENDPOINT                                  = "https://stocrdevarksab01.blob.core.windows.net/"
    }
    dapr = {
      app_id       = "docmind-api"
      app_port     = 8000
      app_protocol = "http"
    }
  }
  llmmagic = {
    name             = "ca-ocr-llmmagic-dev"
    container_name   = "llmmagic"
    image            = "acrocrdevarksab01.azurecr.io/docmind/llmmagic@sha256:bc8a6f7781cc65dd407ba39601233684851cab8f64ceab6545e79c7eb60cbb66"
    target_port      = 8000
    external_enabled = false
    transport        = "auto"
    cpu              = 0.5
    memory           = "1Gi"
    min_replicas     = 1
    max_replicas     = 3
    identity_key     = "llmmagic"
    environment_variables = {
      APPLICATIONINSIGHTS_CONNECTION_STRING                         = "InstrumentationKey=c3a0b40d-62b1-4ac4-8cb2-d508b2a180fb;IngestionEndpoint=https://swedencentral-0.in.applicationinsights.azure.com/;LiveEndpoint=https://swedencentral.livediagnostics.monitor.azure.com/;ApplicationId=6c8c8884-de22-439c-bc70-2d971741af53"
      APPLICATIONINSIGHTS_STATSBEAT_DISABLED_ALL                    = "true"
      DOCMIND_AZURE_MONITOR_ENABLED                                 = "true"
      DOCMIND_AZURE_MONITOR_LIVE_METRICS_ENABLED                    = "false"
      DOCMIND_AZURE_MONITOR_OFFLINE_STORAGE_ENABLED                 = "false"
      DOCMIND_DAPR_HTTP_TIMEOUT_SECONDS                             = "1200"
      DOCMIND_DAPR_RUNTIME_HOST                                     = "127.0.0.1"
      DOCMIND_LLMMAGIC_AZURE_AI_FOUNDRY_ENDPOINT                    = "https://ai-ocr-dev-arksab1.cognitiveservices.azure.com/"
      DOCMIND_LLMMAGIC_AZURE_AI_FOUNDRY_GPT_DEPLOYMENT              = "gpt-5-5"
      DOCMIND_LLMMAGIC_AZURE_AI_FOUNDRY_GPT_MODEL_NAME              = "gpt-5.5"
      DOCMIND_LLMMAGIC_AZURE_AI_FOUNDRY_PROJECT_NAME                = "aifp-ocr-dev-arksab1"
      DOCMIND_LLMMAGIC_AZURE_BLOB_ACCOUNT_URL                       = "https://stocrdevarksab01.blob.core.windows.net/"
      DOCMIND_LLMMAGIC_AZURE_DI_AUTH_MODE                           = "managed_identity"
      DOCMIND_LLMMAGIC_AZURE_DI_ENDPOINT                            = "https://di-ocr-dev-arksab.cognitiveservices.azure.com/"
      DOCMIND_LLMMAGIC_CONTEXT_RESOLVER_BATCH_MAX_ATTRIBUTES        = "10"
      DOCMIND_LLMMAGIC_CONTEXT_RESOLVER_BATCH_MAX_COMPLETION_TOKENS = "20000"
      DOCMIND_LLMMAGIC_CONTEXT_RESOLVER_BATCH_MAX_EVIDENCE_CHARS    = "10000"
      DOCMIND_LLMMAGIC_CONTEXT_RESOLVER_EVIDENCE_TOP_K              = "12"
      DOCMIND_LLMMAGIC_CONTEXT_RESOLVER_MAX_BATCH_ATTEMPTS          = "2"
      DOCMIND_LLMMAGIC_CONTEXT_RESOLVER_MAX_CONCURRENCY             = "2"
      DOCMIND_LLMMAGIC_CONTEXT_RESOLVER_OPENAI_BASE_URL             = "https://ai-ocr-dev-arksab1.cognitiveservices.azure.com/"
      DOCMIND_LLMMAGIC_CONTEXT_RESOLVER_OPENAI_MODEL_ID             = "gpt-5-5"
      DOCMIND_LLMMAGIC_CONTEXT_RESOLVER_REASONING_EFFORT            = "low"
      DOCMIND_LLMMAGIC_CONTEXT_RESOLVER_WORKFLOW_TIMEOUT_SECONDS    = "700"
      DOCMIND_LLMMAGIC_LANGFUSE_ENABLED                             = "false"
      DOCMIND_LLMMAGIC_OCR_FALLBACK_ENABLED                         = "false"
      DOCMIND_LLMMAGIC_OCR_PROVIDER                                 = "azure_document_intelligence"
      OTEL_METRICS_EXPORTER                                         = "none"
      SERVICE_BUS_DOCUMENT_PROCESSING_QUEUE_NAME                    = "document-processing"
      SERVICE_BUS_FULLY_QUALIFIED_NAMESPACE                         = "sb-ocr-dev-arksab.servicebus.windows.net"
      SERVICE_BUS_PROCESSING_RESULTS_QUEUE_NAME                     = "processing-results"
    }
    dapr = {
      app_id       = "docmind-llmmagic"
      app_port     = 8000
      app_protocol = "http"
    }
  }
  worker = {
    name                = "ca-ocr-worker-dev"
    container_name      = "worker"
    image               = "acrocrdevarksab01.azurecr.io/docmind/worker@sha256:c3b3c82483e586458aa84d48f9b71a14fccc3bd76b761e7b6d37ce582bd7f7ad"
    target_port         = 8000
    external_enabled    = false
    transport           = "auto"
    cpu                 = 0.5
    memory              = "1Gi"
    min_replicas        = 1
    max_replicas        = 3
    identity_key        = "worker"
    extra_identity_keys = ["dapr-servicebus-worker"]
    environment_variables = {
      APPLICATIONINSIGHTS_CONNECTION_STRING         = "InstrumentationKey=c3a0b40d-62b1-4ac4-8cb2-d508b2a180fb;IngestionEndpoint=https://swedencentral-0.in.applicationinsights.azure.com/;LiveEndpoint=https://swedencentral.livediagnostics.monitor.azure.com/;ApplicationId=6c8c8884-de22-439c-bc70-2d971741af53"
      APPLICATIONINSIGHTS_STATSBEAT_DISABLED_ALL    = "true"
      DOCMIND_AZURE_MONITOR_ENABLED                 = "true"
      DOCMIND_AZURE_MONITOR_LIVE_METRICS_ENABLED    = "false"
      DOCMIND_AZURE_MONITOR_OFFLINE_STORAGE_ENABLED = "false"
      DOCMIND_CONNECTOR_PROFILE_ID                  = "ps"
      DOCMIND_CONNECTOR_PROFILE_PATH                = "/app/deployments/ps/profile.yml"
      DOCMIND_DAPR_HTTP_TIMEOUT_SECONDS             = "60.0"
      DOCMIND_DAPR_RUNTIME_HOST                     = "127.0.0.1"
      OTEL_METRICS_EXPORTER                         = "none"
      SERVICE_BUS_DOCUMENT_PROCESSING_QUEUE_NAME    = "document-processing"
      SERVICE_BUS_FULLY_QUALIFIED_NAMESPACE         = "sb-ocr-dev-arksab.servicebus.windows.net"
      SERVICE_BUS_PROCESSING_RESULTS_QUEUE_NAME     = "processing-results"
    }
    dapr = {
      app_id       = "docmind-worker"
      app_port     = 8000
      app_protocol = "http"
    }
  }
}

dapr_components = {
  servicebus-pubsub-api = {
    name                         = "docmind-servicebus-pubsub-api"
    component_type               = "pubsub.azure.servicebus.queues"
    version                      = "v1"
    ignore_errors                = false
    init_timeout                 = "5s"
    scopes                       = ["docmind-api"]
    metadata                     = {}
    managed_identity_key         = "dapr-servicebus-api"
    service_bus_metadata_enabled = true
  }
  servicebus-pubsub-worker = {
    name                         = "docmind-servicebus-pubsub-worker"
    component_type               = "pubsub.azure.servicebus.queues"
    version                      = "v1"
    ignore_errors                = false
    init_timeout                 = "5s"
    scopes                       = ["docmind-worker"]
    metadata                     = {}
    managed_identity_key         = "dapr-servicebus-worker"
    service_bus_metadata_enabled = true
  }
}

container_app_jobs = {
  api-migrations = {
    name                       = "caj-ocr-api-migrate-dev"
    container_name             = "api-migrations"
    image                      = "acrocrdevarksab01.azurecr.io/docmind/api@sha256:8615274bb9a4880920c97b28414bd8bbbdb2a8ce1a8c2d780ae365379c40f5e2"
    command                    = ["python"]
    args                       = ["/usr/local/lib/python3.14/site-packages/docmind_api/bootstrap/commands/apply_migrations.py"]
    cpu                        = 0.5
    memory                     = "1Gi"
    replica_timeout_in_seconds = 180
    replica_retry_limit        = 0
    parallelism                = 1
    replica_completion_count   = 1
    identity_key               = "api-migrator"
    registry_identity_key      = "api-migrator"
    environment_variables = {
      DOCMIND_API_DATABASE_ECHO                        = "false"
      DOCMIND_API_DATABASE_POOL_PRE_PING               = "true"
      DOCMIND_API_DATABASE_RUNTIME_PRINCIPAL           = "id-ocr-api-dev"
      DOCMIND_API_DATABASE_RUNTIME_PRINCIPAL_OBJECT_ID = "84ea55cc-37a2-4c64-a020-dcf6d56f61d6"
      DOCMIND_API_DATABASE_URL                         = "postgresql+asyncpg://id-ocr-api-migrator-dev@psql-ocr-dev-arksab.postgres.database.azure.com:5432/db-ocr-dev?ssl=require"
      DOCMIND_API_LOCAL_STARTUP_MIGRATIONS_ENABLED     = "false"
    }
  }
}

tags = {
  application = "ocr"
  customer    = "proservice"
  environment = "dev"
  managed_by  = "terraform"
}
