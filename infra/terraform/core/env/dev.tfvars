subscription_id                 = "fe31d3c8-576f-4c09-913c-635306834ff0"
location                        = "swedencentral"
environment                     = "dev"
tenant_prefix                   = "ee7c45"
app_id                          = "ocr"
instance_number                 = "01"
application_resource_group_name = "rg-ocr-dev"
network_resource_group_name     = "rg-ocr-dev-net"

cmk = {
  storage_key_id               = "https://ee7c45-kv-ocr-dev-01.vault.azure.net/keys/cmk-ocr-dev-storage-01/d9e421f1bc034958aa5989d2137d3402"
  document_intelligence_key_id = "https://ee7c45-kv-ocr-dev-01.vault.azure.net/keys/cmk-ocr-dev-docint-01/373716851d784358b4f05336c5833c36"
  postgresql_key_id            = "https://ee7c45-kv-ocr-dev-01.vault.azure.net/keys/cmk-ocr-dev-postgres-01/d87d4fbc26ab4918ba531bffc80b29f6"
}

virtual_network_name                      = "vnet-ocr-dev"
container_apps_infrastructure_subnet_name = "snet-ocr-dev-aca"

security_design_approved        = true
resource_provider_list_verified = true
runtime_dependencies_ready      = true
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
  sku_name                   = "DataZoneStandard"
  capacity                   = 3000
  dynamic_throttling_enabled = false
  version_upgrade_option     = "NoAutoUpgrade"
}

container_apps = {
  web = {
    container_name        = "web"
    image                 = "ee7c45crocrdev01.azurecr.io/docmind/web@sha256:54bc1d119e4dbae75704886b3381bcf6155b75bf1a8111669d90e41d784521c2"
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
    container_name      = "api"
    image               = "ee7c45crocrdev01.azurecr.io/docmind/api@sha256:35d915f1c3e65168c298cf6fb2feb43129851cdbc204cfbdb246760141032868"
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
      APPLICATIONINSIGHTS_CONNECTION_STRING                  = "InstrumentationKey=77f41fd2-26a5-483b-8331-91bb792c1fca;IngestionEndpoint=https://swedencentral-0.in.applicationinsights.azure.com/;LiveEndpoint=https://swedencentral.livediagnostics.monitor.azure.com/;ApplicationId=bfa7c938-b6cf-43e7-bd61-8df921c67996"
      APPLICATIONINSIGHTS_STATSBEAT_DISABLED_ALL             = "true"
      DOCMIND_API_DATABASE_ECHO                              = "false"
      DOCMIND_API_DATABASE_POOL_PRE_PING                     = "true"
      DOCMIND_API_DATABASE_URL                               = "postgresql+asyncpg://id-ocr-dev-api-01@psql-ocr-dev-01.postgres.database.azure.com:5432/db-ocr-dev-app?ssl=require"
      DOCMIND_API_DIRECT_OCR_INVOCATION_TIMEOUT_SECONDS      = "1200"
      DOCMIND_API_DOCUMENT_STORAGE_AZURE_ACCOUNT_URL         = "https://ee7c45stocrdocdev01.blob.core.windows.net/"
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
      SERVICE_BUS_DOCUMENT_PROCESSING_QUEUE_NAME             = "sbq-ocr-dev-docproc-01"
      SERVICE_BUS_FULLY_QUALIFIED_NAMESPACE                  = "ee7c45sbnsocrdev01.servicebus.windows.net"
      SERVICE_BUS_PROCESSING_RESULTS_QUEUE_NAME              = "sbq-ocr-dev-procres-01"
      STORAGE_ACCOUNT_NAME                                   = "ee7c45stocrdocdev01"
      STORAGE_BLOB_ENDPOINT                                  = "https://ee7c45stocrdocdev01.blob.core.windows.net/"
    }
    dapr = {
      app_id       = "docmind-api"
      app_port     = 8000
      app_protocol = "http"
    }
  }
  llmmagic = {
    container_name   = "llmmagic"
    image            = "ee7c45crocrdev01.azurecr.io/docmind/llmmagic@sha256:00eb49f65bb07d8d8a99acc6c69454b03633c11601b2cc5c5c76e4e3b9151612"
    target_port      = 8000
    external_enabled = false
    transport        = "auto"
    cpu              = 0.5
    memory           = "1Gi"
    min_replicas     = 1
    max_replicas     = 3
    identity_key     = "llmmagic"
    environment_variables = {
      APPLICATIONINSIGHTS_CONNECTION_STRING                         = "InstrumentationKey=77f41fd2-26a5-483b-8331-91bb792c1fca;IngestionEndpoint=https://swedencentral-0.in.applicationinsights.azure.com/;LiveEndpoint=https://swedencentral.livediagnostics.monitor.azure.com/;ApplicationId=bfa7c938-b6cf-43e7-bd61-8df921c67996"
      APPLICATIONINSIGHTS_STATSBEAT_DISABLED_ALL                    = "true"
      DOCMIND_AZURE_MONITOR_ENABLED                                 = "true"
      DOCMIND_AZURE_MONITOR_LIVE_METRICS_ENABLED                    = "false"
      DOCMIND_AZURE_MONITOR_OFFLINE_STORAGE_ENABLED                 = "false"
      DOCMIND_DAPR_HTTP_TIMEOUT_SECONDS                             = "1200"
      DOCMIND_DAPR_RUNTIME_HOST                                     = "127.0.0.1"
      DOCMIND_LLMMAGIC_AZURE_AI_FOUNDRY_ENDPOINT                    = "https://ais-ocr-dev-01.cognitiveservices.azure.com/"
      DOCMIND_LLMMAGIC_AZURE_AI_FOUNDRY_GPT_DEPLOYMENT              = "dep-ocr-dev-gpt55-01"
      DOCMIND_LLMMAGIC_AZURE_AI_FOUNDRY_GPT_MODEL_NAME              = "gpt-5.5"
      DOCMIND_LLMMAGIC_AZURE_AI_FOUNDRY_PROJECT_NAME                = "proj-ocr-dev-01"
      DOCMIND_LLMMAGIC_AZURE_BLOB_ACCOUNT_URL                       = "https://ee7c45stocrdocdev01.blob.core.windows.net/"
      DOCMIND_LLMMAGIC_AZURE_DI_AUTH_MODE                           = "managed_identity"
      DOCMIND_LLMMAGIC_AZURE_DI_ENDPOINT                            = "https://ee7c45diocrdev01.cognitiveservices.azure.com/"
      DOCMIND_LLMMAGIC_CONTEXT_RESOLVER_BATCH_MAX_ATTRIBUTES        = "10"
      DOCMIND_LLMMAGIC_CONTEXT_RESOLVER_BATCH_MAX_COMPLETION_TOKENS = "20000"
      DOCMIND_LLMMAGIC_CONTEXT_RESOLVER_BATCH_MAX_EVIDENCE_CHARS    = "10000"
      DOCMIND_LLMMAGIC_CONTEXT_RESOLVER_EVIDENCE_TOP_K              = "12"
      DOCMIND_LLMMAGIC_CONTEXT_RESOLVER_MAX_BATCH_ATTEMPTS          = "2"
      DOCMIND_LLMMAGIC_CONTEXT_RESOLVER_MAX_CONCURRENCY             = "2"
      DOCMIND_LLMMAGIC_CONTEXT_RESOLVER_OPENAI_BASE_URL             = "https://ais-ocr-dev-01.cognitiveservices.azure.com/"
      DOCMIND_LLMMAGIC_CONTEXT_RESOLVER_OPENAI_MODEL_ID             = "dep-ocr-dev-gpt55-01"
      DOCMIND_LLMMAGIC_CONTEXT_RESOLVER_REASONING_EFFORT            = "low"
      DOCMIND_LLMMAGIC_CONTEXT_RESOLVER_WORKFLOW_TIMEOUT_SECONDS    = "700"
      DOCMIND_LLMMAGIC_LANGFUSE_ENABLED                             = "false"
      DOCMIND_LLMMAGIC_OCR_FALLBACK_ENABLED                         = "false"
      DOCMIND_LLMMAGIC_OCR_PROVIDER                                 = "azure_document_intelligence"
      OTEL_METRICS_EXPORTER                                         = "none"
      SERVICE_BUS_DOCUMENT_PROCESSING_QUEUE_NAME                    = "sbq-ocr-dev-docproc-01"
      SERVICE_BUS_FULLY_QUALIFIED_NAMESPACE                         = "ee7c45sbnsocrdev01.servicebus.windows.net"
      SERVICE_BUS_PROCESSING_RESULTS_QUEUE_NAME                     = "sbq-ocr-dev-procres-01"
    }
    dapr = {
      app_id       = "docmind-llmmagic"
      app_port     = 8000
      app_protocol = "http"
    }
  }
  worker = {
    container_name      = "worker"
    image               = "ee7c45crocrdev01.azurecr.io/docmind/worker@sha256:5344e68f4131d339dfb616beeb2b265068a171137772e9389b2d6ef3130a9bb9"
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
      APPLICATIONINSIGHTS_CONNECTION_STRING         = "InstrumentationKey=77f41fd2-26a5-483b-8331-91bb792c1fca;IngestionEndpoint=https://swedencentral-0.in.applicationinsights.azure.com/;LiveEndpoint=https://swedencentral.livediagnostics.monitor.azure.com/;ApplicationId=bfa7c938-b6cf-43e7-bd61-8df921c67996"
      APPLICATIONINSIGHTS_STATSBEAT_DISABLED_ALL    = "true"
      DOCMIND_AZURE_MONITOR_ENABLED                 = "true"
      DOCMIND_AZURE_MONITOR_LIVE_METRICS_ENABLED    = "false"
      DOCMIND_AZURE_MONITOR_OFFLINE_STORAGE_ENABLED = "false"
      DOCMIND_CONNECTOR_PROFILE_ID                  = "ps"
      DOCMIND_CONNECTOR_PROFILE_PATH                = "/app/deployments/ps/profile.yml"
      DOCMIND_DAPR_HTTP_TIMEOUT_SECONDS             = "60.0"
      DOCMIND_DAPR_RUNTIME_HOST                     = "127.0.0.1"
      OTEL_METRICS_EXPORTER                         = "none"
      SERVICE_BUS_DOCUMENT_PROCESSING_QUEUE_NAME    = "sbq-ocr-dev-docproc-01"
      SERVICE_BUS_FULLY_QUALIFIED_NAMESPACE         = "ee7c45sbnsocrdev01.servicebus.windows.net"
      SERVICE_BUS_PROCESSING_RESULTS_QUEUE_NAME     = "sbq-ocr-dev-procres-01"
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
    container_name             = "api-migrations"
    image                      = "ee7c45crocrdev01.azurecr.io/docmind/api@sha256:35d915f1c3e65168c298cf6fb2feb43129851cdbc204cfbdb246760141032868"
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
      DOCMIND_API_DATABASE_RUNTIME_PRINCIPAL           = "id-ocr-dev-api-01"
      DOCMIND_API_DATABASE_RUNTIME_PRINCIPAL_OBJECT_ID = "a442a4d2-52ac-44a4-bd61-5a177acb8fa1"
      DOCMIND_API_DATABASE_URL                         = "postgresql+asyncpg://id-ocr-dev-api-migrator-01@psql-ocr-dev-01.postgres.database.azure.com:5432/db-ocr-dev-app?ssl=require"
      DOCMIND_API_LOCAL_STARTUP_MIGRATIONS_ENABLED     = "false"
    }
  }
}

tags = {
  application  = "ocr"
  environment  = "dev"
  managed_by   = "terraform"
  organization = "psf"
}
