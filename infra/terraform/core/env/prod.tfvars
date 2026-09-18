subscription_id                 = "832f8765-ba78-4d5b-8330-e8edd672152f"
location                        = "swedencentral"
environment                     = "prod"
tenant_prefix                   = "ee7c45"
app_id                          = "ocr"
instance_number                 = "01"
application_resource_group_name = "rg-ocr-prod"
network_resource_group_name     = "rg-ocr-prod-net"

virtual_network_name                      = "vnet-ocr-prod"
container_apps_infrastructure_subnet_name = "snet-ocr-prod-aca"

cmk = {
  storage_key_id               = "https://ee7c45-kv-ocr-prod-01.vault.azure.net/keys/cmk-ocr-prod-storage-01/1dc35600ac174a2d84ef3430acb4411f"
  document_intelligence_key_id = "https://ee7c45-kv-ocr-prod-01.vault.azure.net/keys/cmk-ocr-prod-docint-01/593f349d2c7a491cb2c4c0809c8eb581"
  postgresql_key_id            = "https://ee7c45-kv-ocr-prod-01.vault.azure.net/keys/cmk-ocr-prod-postgres-01/4785c8aabd6d400889aca2c52d1a18c9"
}


security_design_approved        = true
resource_provider_list_verified = true
runtime_dependencies_ready      = true
foundry_enabled                 = true
langfuse_tracing = {
  # Enable only after Langfuse Core is deployed in PROD.
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

container_apps = {
  web = {
    container_name        = "web"
    image                 = "ee7c45crocrprod01.azurecr.io/docmind/web@sha256:3f80c5a3838cba0a322e01b2efa6a3e42f48e02dde4bbd68b6aeaa1b9236d356"
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
    image               = "ee7c45crocrprod01.azurecr.io/docmind/api@sha256:2db5acf212b4f2244e387611b694a9f788f56fb24ca36d007448bf9e98025f95"
    target_port         = 8000
    external_enabled    = true
    transport           = "auto"
    cpu                 = 1
    memory              = "2Gi"
    min_replicas        = 1
    max_replicas        = 5
    identity_key        = "api"
    extra_identity_keys = ["dapr-servicebus-api"]
    health_probes = {
      startup = {
        path                    = "/health/live"
        interval_seconds        = 10
        timeout                 = 5
        failure_count_threshold = 30
      }
      liveness = {
        path                    = "/health/live"
        interval_seconds        = 30
        timeout                 = 5
        failure_count_threshold = 3
      }
      readiness = {
        path                    = "/health/ready"
        interval_seconds        = 10
        timeout                 = 5
        failure_count_threshold = 3
      }
    }
    environment_variables = {
      APPLICATIONINSIGHTS_CONNECTION_STRING                  = "InstrumentationKey=937d64ed-41d5-41da-a00c-5c052d8caa16;IngestionEndpoint=https://swedencentral-0.in.applicationinsights.azure.com/;LiveEndpoint=https://swedencentral.livediagnostics.monitor.azure.com/;ApplicationId=942d3d81-55a8-44e3-b1ff-e9085e5e7755"
      APPLICATIONINSIGHTS_STATSBEAT_DISABLED_ALL             = "true"
      DOCMIND_API_DATABASE_ECHO                              = "false"
      DOCMIND_API_DATABASE_POOL_PRE_PING                     = "true"
      DOCMIND_API_DATABASE_URL                               = "postgresql+asyncpg://id-ocr-prod-api-01@psql-ocr-prod-01.postgres.database.azure.com:5432/db-ocr-prod-app?ssl=require"
      DOCMIND_API_DIRECT_OCR_INVOCATION_TIMEOUT_SECONDS      = "1200"
      DOCMIND_API_DOCUMENT_STORAGE_AZURE_ACCOUNT_URL         = "https://ee7c45stocrdocprod01.blob.core.windows.net/"
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
      DOCMIND_API_OCR_EVENT_PUBSUB_NAME                      = "docmind-servicebus-pubsub-api"
      OTEL_METRICS_EXPORTER                                  = "none"
      SERVICE_BUS_DOCUMENT_PROCESSING_QUEUE_NAME             = "document-processing"
      SERVICE_BUS_FULLY_QUALIFIED_NAMESPACE                  = "ee7c45sbnsocrprod01.servicebus.windows.net"
      SERVICE_BUS_PROCESSING_RESULTS_QUEUE_NAME              = "processing-results"
      STORAGE_ACCOUNT_NAME                                   = "ee7c45stocrdocprod01"
      STORAGE_BLOB_ENDPOINT                                  = "https://ee7c45stocrdocprod01.blob.core.windows.net/"
    }
    dapr = {
      app_id       = "docmind-api"
      app_port     = 8000
      app_protocol = "http"
    }
  }
  llmmagic = {
    container_name      = "llmmagic"
    image               = "ee7c45crocrprod01.azurecr.io/docmind/llmmagic@sha256:c0ba46ed1c9d7f1dfe54cb8f7601eae31c53f527eda6b601135c3668d83ff8e1"
    target_port         = 8000
    external_enabled    = false
    transport           = "auto"
    cpu                 = 0.5
    memory              = "1Gi"
    min_replicas        = 1
    max_replicas        = 3
    identity_key        = "llmmagic"
    extra_identity_keys = ["dapr-servicebus-llmmagic"]
    health_probes = {
      startup = {
        path                    = "/health/live"
        interval_seconds        = 10
        timeout                 = 5
        failure_count_threshold = 30
      }
      liveness = {
        path                    = "/health/live"
        interval_seconds        = 30
        timeout                 = 5
        failure_count_threshold = 3
      }
      readiness = {
        path                    = "/health/ready"
        interval_seconds        = 10
        timeout                 = 5
        failure_count_threshold = 3
      }
    }
    environment_variables = {
      APPLICATIONINSIGHTS_CONNECTION_STRING                         = "InstrumentationKey=937d64ed-41d5-41da-a00c-5c052d8caa16;IngestionEndpoint=https://swedencentral-0.in.applicationinsights.azure.com/;LiveEndpoint=https://swedencentral.livediagnostics.monitor.azure.com/;ApplicationId=942d3d81-55a8-44e3-b1ff-e9085e5e7755"
      APPLICATIONINSIGHTS_STATSBEAT_DISABLED_ALL                    = "true"
      DOCMIND_AZURE_MONITOR_ENABLED                                 = "true"
      DOCMIND_AZURE_MONITOR_LIVE_METRICS_ENABLED                    = "false"
      DOCMIND_AZURE_MONITOR_OFFLINE_STORAGE_ENABLED                 = "false"
      DOCMIND_DAPR_HTTP_TIMEOUT_SECONDS                             = "1200"
      DOCMIND_DAPR_RUNTIME_HOST                                     = "127.0.0.1"
      DOCMIND_LLMMAGIC_AZURE_AI_FOUNDRY_ENDPOINT                    = "https://ais-ocr-prod-01.cognitiveservices.azure.com/"
      DOCMIND_LLMMAGIC_AZURE_AI_FOUNDRY_GPT_DEPLOYMENT              = "dep-ocr-prod-gpt55-01"
      DOCMIND_LLMMAGIC_AZURE_AI_FOUNDRY_GPT_MODEL_NAME              = "gpt-5.5"
      DOCMIND_LLMMAGIC_AZURE_AI_FOUNDRY_PROJECT_NAME                = "proj-ocr-prod-01"
      DOCMIND_LLMMAGIC_AZURE_BLOB_ACCOUNT_URL                       = "https://ee7c45stocrdocprod01.blob.core.windows.net/"
      DOCMIND_LLMMAGIC_AZURE_DI_AUTH_MODE                           = "managed_identity"
      DOCMIND_LLMMAGIC_AZURE_DI_ENDPOINT                            = "https://ee7c45diocrprod01.cognitiveservices.azure.com/"
      DOCMIND_LLMMAGIC_CONTEXT_RESOLVER_BATCH_MAX_ATTRIBUTES        = "10"
      DOCMIND_LLMMAGIC_CONTEXT_RESOLVER_BATCH_MAX_COMPLETION_TOKENS = "20000"
      DOCMIND_LLMMAGIC_CONTEXT_RESOLVER_BATCH_MAX_EVIDENCE_CHARS    = "10000"
      DOCMIND_LLMMAGIC_CONTEXT_RESOLVER_EVIDENCE_TOP_K              = "12"
      DOCMIND_LLMMAGIC_CONTEXT_RESOLVER_MAX_BATCH_ATTEMPTS          = "2"
      DOCMIND_LLMMAGIC_CONTEXT_RESOLVER_MAX_CONCURRENCY             = "2"
      DOCMIND_LLMMAGIC_CONTEXT_RESOLVER_OPENAI_BASE_URL             = "https://ais-ocr-prod-01.cognitiveservices.azure.com/"
      DOCMIND_LLMMAGIC_CONTEXT_RESOLVER_OPENAI_MODEL_ID             = "dep-ocr-prod-gpt55-01"
      DOCMIND_LLMMAGIC_CONTEXT_RESOLVER_REASONING_EFFORT            = "low"
      DOCMIND_LLMMAGIC_CONTEXT_RESOLVER_WORKFLOW_TIMEOUT_SECONDS    = "700"
      DOCMIND_LLMMAGIC_OCR_FALLBACK_ENABLED                         = "false"
      DOCMIND_LLMMAGIC_OCR_PROVIDER                                 = "azure_document_intelligence"
      OTEL_METRICS_EXPORTER                                         = "none"
      SERVICE_BUS_DOCUMENT_PROCESSING_QUEUE_NAME                    = "document-processing"
      SERVICE_BUS_FULLY_QUALIFIED_NAMESPACE                         = "ee7c45sbnsocrprod01.servicebus.windows.net"
      SERVICE_BUS_PROCESSING_RESULTS_QUEUE_NAME                     = "processing-results"
    }
    dapr = {
      app_id       = "docmind-llmmagic"
      app_port     = 8000
      app_protocol = "http"
    }
  }
  worker = {
    container_name      = "worker"
    image               = "ee7c45crocrprod01.azurecr.io/docmind/worker@sha256:0b0e06162da54c8ab208a57b5ef9316cf8ab4ee95a67594a54eace5236a536b9"
    target_port         = 8000
    external_enabled    = false
    transport           = "auto"
    cpu                 = 0.5
    memory              = "1Gi"
    min_replicas        = 1
    max_replicas        = 3
    identity_key        = "worker"
    extra_identity_keys = ["dapr-servicebus-worker"]
    health_probes = {
      startup = {
        path                    = "/health/live"
        interval_seconds        = 10
        timeout                 = 5
        failure_count_threshold = 30
      }
      liveness = {
        path                    = "/health/live"
        interval_seconds        = 30
        timeout                 = 5
        failure_count_threshold = 3
      }
      readiness = {
        path                    = "/health/ready"
        interval_seconds        = 10
        timeout                 = 5
        failure_count_threshold = 3
      }
    }
    environment_variables = {
      APPLICATIONINSIGHTS_CONNECTION_STRING         = "InstrumentationKey=937d64ed-41d5-41da-a00c-5c052d8caa16;IngestionEndpoint=https://swedencentral-0.in.applicationinsights.azure.com/;LiveEndpoint=https://swedencentral.livediagnostics.monitor.azure.com/;ApplicationId=942d3d81-55a8-44e3-b1ff-e9085e5e7755"
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
      SERVICE_BUS_FULLY_QUALIFIED_NAMESPACE         = "ee7c45sbnsocrprod01.servicebus.windows.net"
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
  servicebus-pubsub-llmmagic = {
    name                         = "docmind-servicebus-pubsub-llmmagic"
    component_type               = "pubsub.azure.servicebus.queues"
    version                      = "v1"
    ignore_errors                = false
    init_timeout                 = "5s"
    scopes                       = ["docmind-llmmagic"]
    metadata                     = {}
    managed_identity_key         = "dapr-servicebus-llmmagic"
    service_bus_metadata_enabled = true
  }
}

container_app_jobs = {
  api-migrations = {
    container_name             = "api-migrations"
    image                      = "ee7c45crocrprod01.azurecr.io/docmind/api@sha256:2db5acf212b4f2244e387611b694a9f788f56fb24ca36d007448bf9e98025f95"
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
      DOCMIND_API_DATABASE_RUNTIME_PRINCIPAL           = "id-ocr-prod-api-01"
      DOCMIND_API_DATABASE_RUNTIME_PRINCIPAL_OBJECT_ID = "71dae250-b382-497b-bd93-b9b38c62bb6a"
      DOCMIND_API_DATABASE_URL                         = "postgresql+asyncpg://id-ocr-prod-api-migrator-01@psql-ocr-prod-01.postgres.database.azure.com:5432/db-ocr-prod-app?ssl=require"
      DOCMIND_API_LOCAL_STARTUP_MIGRATIONS_ENABLED     = "false"
    }
  }
}

tags = {
  application  = "ocr"
  environment  = "prod"
  managed_by   = "terraform"
  organization = "psf"
}
