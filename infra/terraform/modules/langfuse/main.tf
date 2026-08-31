locals {
  clickhouse_storage_name = "langfuse-clickhouse"
  clickhouse_share_name   = "langfuse-clickhouse"
  postgres_storage_name   = "langfuse-postgres"
  postgres_share_name     = "langfuse-postgres"
  valkey_storage_name     = "langfuse-valkey"
  valkey_share_name       = "langfuse-valkey"
  blob_container_name     = "langfuse"
  web_origin              = "https://${var.workloads.web.name}.${var.container_app_environment_default_domain}"

  key_vault_secrets = {
    clickhouse-password = var.secret_names.clickhouse_password
    encryption-key      = var.secret_names.encryption_key
    init-public-key     = var.secret_names.init_project_public_key
    init-secret-key     = var.secret_names.init_project_secret_key
    nextauth-secret     = var.secret_names.nextauth_secret
    postgres-password   = var.secret_names.postgres_password
    salt                = var.secret_names.salt
    valkey-password     = var.secret_names.valkey_password
  }

  common_environment = var.enabled ? {
    NEXTAUTH_URL                           = local.web_origin
    DATABASE_HOST                          = "${var.workloads.postgres.name}:5432"
    DATABASE_USERNAME                      = "langfuse"
    DATABASE_NAME                          = "langfuse"
    CLICKHOUSE_URL                         = "http://${var.workloads.clickhouse.name}"
    CLICKHOUSE_MIGRATION_URL               = "clickhouse://${var.workloads.clickhouse.name}:9000"
    CLICKHOUSE_USER                        = "clickhouse"
    CLICKHOUSE_CLUSTER_ENABLED             = "false"
    CLICKHOUSE_MIGRATION_SSL               = "false"
    REDIS_HOST                             = var.workloads.valkey.name
    REDIS_PORT                             = "6379"
    REDIS_USERNAME                         = "default"
    LANGFUSE_USE_AZURE_BLOB                = "true"
    LANGFUSE_S3_EVENT_UPLOAD_BUCKET        = local.blob_container_name
    LANGFUSE_S3_EVENT_UPLOAD_ACCESS_KEY_ID = azurerm_storage_account.this[0].name
    LANGFUSE_S3_EVENT_UPLOAD_ENDPOINT      = trimsuffix(azurerm_storage_account.this[0].primary_blob_endpoint, "/")
    LANGFUSE_S3_EVENT_UPLOAD_PREFIX        = "events/"
    LANGFUSE_S3_MEDIA_UPLOAD_BUCKET        = local.blob_container_name
    LANGFUSE_S3_MEDIA_UPLOAD_ACCESS_KEY_ID = azurerm_storage_account.this[0].name
    LANGFUSE_S3_MEDIA_UPLOAD_ENDPOINT      = trimsuffix(azurerm_storage_account.this[0].primary_blob_endpoint, "/")
    LANGFUSE_S3_MEDIA_UPLOAD_PREFIX        = "media/"
    LANGFUSE_S3_BATCH_EXPORT_ENABLED       = "false"
    TELEMETRY_ENABLED                      = "false"
    AUTH_DISABLE_SIGNUP                    = "false"
    LANGFUSE_LOG_FORMAT                    = "json"
    LANGFUSE_ENABLE_EXPERIMENTAL_FEATURES  = "false"
    NODE_OPTIONS                           = var.node_options
  } : {}

  web_environment = {
    LANGFUSE_INIT_ORG_ID          = "docmind"
    LANGFUSE_INIT_ORG_NAME        = "DocMind"
    LANGFUSE_INIT_PROJECT_ID      = "docmind-${var.environment}"
    LANGFUSE_INIT_PROJECT_NAME    = "DocMind ${upper(var.environment)}"
    LANGFUSE_DEFAULT_ORG_ID       = "docmind"
    LANGFUSE_DEFAULT_ORG_ROLE     = "ADMIN"
    LANGFUSE_DEFAULT_PROJECT_ID   = "docmind-${var.environment}"
    LANGFUSE_DEFAULT_PROJECT_ROLE = "ADMIN"
  }
}

resource "azurerm_container_app" "web" {
  count = var.enabled && var.runtime_enabled ? 1 : 0

  name                         = var.workloads.web.name
  container_app_environment_id = var.container_app_environment_id
  resource_group_name          = var.resource_group_name
  revision_mode                = "Single"
  workload_profile_name        = "Consumption"

  identity {
    type         = "UserAssigned"
    identity_ids = [var.workloads.web.identity_id]
  }

  registry {
    server   = var.registry_server
    identity = var.workloads.web.identity_id
  }

  dynamic "secret" {
    for_each = local.key_vault_secrets

    content {
      name                = secret.key
      key_vault_secret_id = "${trimsuffix(var.key_vault_uri, "/")}/secrets/${secret.value}"
      identity            = var.workloads.web.identity_id
    }
  }

  secret {
    name  = "blob-access-key"
    value = azurerm_storage_account.this[0].primary_access_key
  }

  ingress {
    allow_insecure_connections = false
    external_enabled           = true
    target_port                = 3000
    transport                  = "auto"

    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  template {
    min_replicas = 1
    max_replicas = 2

    http_scale_rule {
      name                = "web-http"
      concurrent_requests = var.web_http_concurrent_requests
    }

    container {
      name   = "langfuse-web"
      image  = var.workloads.web.image
      cpu    = var.web_cpu
      memory = var.web_memory

      dynamic "env" {
        for_each = merge(
          local.common_environment,
          local.web_environment,
          { AZURE_CLIENT_ID = var.workloads.web.identity_client_id },
        )

        content {
          name  = env.key
          value = env.value
        }
      }

      dynamic "env" {
        for_each = {
          CLICKHOUSE_PASSWORD                        = "clickhouse-password"
          DATABASE_PASSWORD                          = "postgres-password"
          ENCRYPTION_KEY                             = "encryption-key"
          LANGFUSE_INIT_PROJECT_PUBLIC_KEY           = "init-public-key"
          LANGFUSE_INIT_PROJECT_SECRET_KEY           = "init-secret-key"
          LANGFUSE_S3_EVENT_UPLOAD_SECRET_ACCESS_KEY = "blob-access-key"
          LANGFUSE_S3_MEDIA_UPLOAD_SECRET_ACCESS_KEY = "blob-access-key"
          NEXTAUTH_SECRET                            = "nextauth-secret"
          REDIS_AUTH                                 = "valkey-password"
          SALT                                       = "salt"
        }

        content {
          name        = env.key
          secret_name = env.value
        }
      }

      startup_probe {
        transport               = "HTTP"
        port                    = 3000
        path                    = "/api/public/health"
        interval_seconds        = 10
        timeout                 = 5
        failure_count_threshold = 30
      }

      liveness_probe {
        transport               = "HTTP"
        port                    = 3000
        path                    = "/api/public/health"
        interval_seconds        = 30
        timeout                 = 5
        failure_count_threshold = 3
      }

      readiness_probe {
        transport               = "HTTP"
        port                    = 3000
        path                    = "/api/public/health"
        interval_seconds        = 10
        timeout                 = 5
        failure_count_threshold = 3
        success_count_threshold = 1
      }
    }
  }

  tags = var.tags

  depends_on = [
    azapi_resource.blob_container,
    azurerm_private_endpoint.blob,
    azapi_resource.clickhouse,
    azurerm_container_app.postgres,
    azurerm_container_app.valkey,
  ]

  lifecycle {
    precondition {
      condition     = var.private_access_enabled
      error_message = "Langfuse Web may be enabled only when the shared Container Apps Environment uses the approved VPN/private-ingress cutoff."
    }

    precondition {
      condition     = var.environment == "dev"
      error_message = "The current Langfuse ACA topology is approved only for the DEV environment."
    }
  }
}

resource "azurerm_container_app" "worker" {
  count = var.enabled && var.runtime_enabled ? 1 : 0

  name                         = var.workloads.worker.name
  container_app_environment_id = var.container_app_environment_id
  resource_group_name          = var.resource_group_name
  revision_mode                = "Single"
  workload_profile_name        = "Consumption"

  identity {
    type         = "UserAssigned"
    identity_ids = [var.workloads.worker.identity_id]
  }

  registry {
    server   = var.registry_server
    identity = var.workloads.worker.identity_id
  }

  dynamic "secret" {
    for_each = {
      for key, value in local.key_vault_secrets : key => value
      if !contains(["init-public-key", "init-secret-key", "nextauth-secret"], key)
    }

    content {
      name                = secret.key
      key_vault_secret_id = "${trimsuffix(var.key_vault_uri, "/")}/secrets/${secret.value}"
      identity            = var.workloads.worker.identity_id
    }
  }

  secret {
    name  = "blob-access-key"
    value = azurerm_storage_account.this[0].primary_access_key
  }

  template {
    min_replicas = 1
    max_replicas = 2

    custom_scale_rule {
      name             = "worker-cpu"
      custom_rule_type = "cpu"
      metadata = {
        type  = "Utilization"
        value = tostring(var.worker_cpu_scale_threshold)
      }
    }

    container {
      name   = "langfuse-worker"
      image  = var.workloads.worker.image
      cpu    = var.worker_cpu
      memory = var.worker_memory

      dynamic "env" {
        for_each = merge(local.common_environment, {
          AZURE_CLIENT_ID = var.workloads.worker.identity_client_id
        })

        content {
          name  = env.key
          value = env.value
        }
      }

      dynamic "env" {
        for_each = {
          CLICKHOUSE_PASSWORD                        = "clickhouse-password"
          DATABASE_PASSWORD                          = "postgres-password"
          ENCRYPTION_KEY                             = "encryption-key"
          LANGFUSE_S3_EVENT_UPLOAD_SECRET_ACCESS_KEY = "blob-access-key"
          LANGFUSE_S3_MEDIA_UPLOAD_SECRET_ACCESS_KEY = "blob-access-key"
          REDIS_AUTH                                 = "valkey-password"
          SALT                                       = "salt"
        }

        content {
          name        = env.key
          secret_name = env.value
        }
      }

      startup_probe {
        transport               = "HTTP"
        port                    = 3030
        path                    = "/api/health"
        interval_seconds        = 10
        timeout                 = 5
        failure_count_threshold = 30
      }

      liveness_probe {
        transport               = "HTTP"
        port                    = 3030
        path                    = "/api/health"
        interval_seconds        = 30
        timeout                 = 5
        failure_count_threshold = 3
      }

      readiness_probe {
        transport               = "HTTP"
        port                    = 3030
        path                    = "/api/health"
        interval_seconds        = 10
        timeout                 = 5
        failure_count_threshold = 3
        success_count_threshold = 1
      }
    }
  }

  tags = var.tags

  depends_on = [
    azapi_resource.blob_container,
    azurerm_private_endpoint.blob,
    azapi_resource.clickhouse,
    azurerm_container_app.postgres,
    azurerm_container_app.valkey,
  ]
}

resource "azapi_resource" "clickhouse" {
  count = var.enabled && var.runtime_enabled ? 1 : 0

  type      = "Microsoft.App/containerApps@2025-01-01"
  name      = var.workloads.clickhouse.name
  parent_id = join("/", slice(split("/", var.container_app_environment_id), 0, 5))
  location  = var.location
  identity {
    type = "UserAssigned"
    identity_ids = [
      var.workloads.clickhouse.identity_id,
    ]
  }
  body = {
    properties = {
      environmentId = var.container_app_environment_id
      configuration = {
        activeRevisionsMode = "Single"
        registries = [{
          server   = var.registry_server
          identity = var.workloads.clickhouse.identity_id
        }]
        secrets = [{
          name        = "clickhouse-password"
          keyVaultUrl = "${trimsuffix(var.key_vault_uri, "/")}/secrets/${var.secret_names.clickhouse_password}"
          identity    = var.workloads.clickhouse.identity_id
        }]
        ingress = {
          external   = false
          targetPort = 8123
          transport  = "http"
          traffic = [{
            latestRevision = true
            weight         = 100
          }]
          additionalPortMappings = [{
            external    = false
            targetPort  = 9000
            exposedPort = 9000
          }]
        }
      }
      workloadProfileName = var.clickhouse_workload_profile_name
      template = {
        scale = {
          minReplicas = 1
          maxReplicas = 1
        }
        containers = [{
          name  = "clickhouse"
          image = var.workloads.clickhouse.image
          env = [
            {
              name  = "CLICKHOUSE_DB"
              value = "default"
            },
            {
              name  = "CLICKHOUSE_USER"
              value = "clickhouse"
            },
            {
              name      = "CLICKHOUSE_PASSWORD"
              secretRef = "clickhouse-password"
            },
          ]
          resources = {
            cpu    = var.clickhouse_cpu
            memory = var.clickhouse_memory
          }
          probes = [
            {
              type = "Startup"
              httpGet = {
                path   = "/ping"
                port   = 8123
                scheme = "HTTP"
              }
              periodSeconds    = 10
              timeoutSeconds   = 5
              failureThreshold = 30
            },
            {
              type = "Liveness"
              httpGet = {
                path   = "/ping"
                port   = 8123
                scheme = "HTTP"
              }
              periodSeconds    = 30
              timeoutSeconds   = 5
              failureThreshold = 3
            },
            {
              type = "Readiness"
              httpGet = {
                path   = "/ping"
                port   = 8123
                scheme = "HTTP"
              }
              periodSeconds    = 10
              timeoutSeconds   = 5
              failureThreshold = 3
              successThreshold = 1
            },
          ]
          volumeMounts = [{
            volumeName = "clickhouse-data"
            mountPath  = "/var/lib/clickhouse"
          }]
        }]
        volumes = [{
          name        = "clickhouse-data"
          storageType = "NfsAzureFile"
          storageName = local.clickhouse_storage_name
        }]
      }
    }
    tags = var.tags
  }

  schema_validation_enabled = false

  depends_on = [azapi_resource.clickhouse_environment_storage]

  lifecycle {
    precondition {
      condition     = var.clickhouse_cpu >= 4 && try(tonumber(trimsuffix(var.clickhouse_memory, "Gi")) >= 16, false)
      error_message = "ClickHouse requires at least 4 vCPU and 16 GiB on the dedicated workload profile."
    }
  }
}
