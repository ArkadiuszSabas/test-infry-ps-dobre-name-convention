resource "azurerm_container_app" "postgres" {
  count = var.enabled ? 1 : 0

  name                         = var.workloads.postgres.name
  container_app_environment_id = var.container_app_environment_id
  resource_group_name          = var.resource_group_name
  revision_mode                = "Single"
  workload_profile_name        = "Consumption"

  identity {
    type         = "UserAssigned"
    identity_ids = [var.workloads.postgres.identity_id]
  }

  registry {
    server   = var.registry_server
    identity = var.workloads.postgres.identity_id
  }

  secret {
    name                = "postgres-password"
    key_vault_secret_id = "${trimsuffix(var.key_vault_uri, "/")}/secrets/${var.secret_names.postgres_password}"
    identity            = var.workloads.postgres.identity_id
  }

  ingress {
    external_enabled = false
    target_port      = 5432
    transport        = "tcp"

    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  template {
    min_replicas = 1
    max_replicas = 1

    container {
      name   = "postgres"
      image  = var.workloads.postgres.image
      cpu    = var.postgres_cpu
      memory = var.postgres_memory

      env {
        name  = "POSTGRES_DB"
        value = "langfuse"
      }

      env {
        name  = "POSTGRES_USER"
        value = "langfuse"
      }

      env {
        name        = "POSTGRES_PASSWORD"
        secret_name = "postgres-password"
      }

      env {
        name  = "PGDATA"
        value = "/var/lib/postgresql/data/pgdata"
      }

      volume_mounts {
        name = "postgres-data"
        path = "/var/lib/postgresql/data"
      }

      startup_probe {
        transport               = "TCP"
        port                    = 5432
        interval_seconds        = 10
        timeout                 = 5
        failure_count_threshold = 30
      }

      liveness_probe {
        transport               = "TCP"
        port                    = 5432
        interval_seconds        = 30
        timeout                 = 5
        failure_count_threshold = 3
      }

      readiness_probe {
        transport               = "TCP"
        port                    = 5432
        interval_seconds        = 10
        timeout                 = 5
        failure_count_threshold = 3
        success_count_threshold = 1
      }
    }

    volume {
      name         = "postgres-data"
      storage_name = local.postgres_storage_name
      storage_type = "NfsAzureFile"
    }
  }

  tags       = var.tags
  depends_on = [azapi_resource.postgres_environment_storage]
}

resource "azurerm_container_app" "valkey" {
  count = var.enabled ? 1 : 0

  name                         = var.workloads.valkey.name
  container_app_environment_id = var.container_app_environment_id
  resource_group_name          = var.resource_group_name
  revision_mode                = "Single"
  workload_profile_name        = "Consumption"

  identity {
    type         = "UserAssigned"
    identity_ids = [var.workloads.valkey.identity_id]
  }

  registry {
    server   = var.registry_server
    identity = var.workloads.valkey.identity_id
  }

  secret {
    name                = "valkey-password"
    key_vault_secret_id = "${trimsuffix(var.key_vault_uri, "/")}/secrets/${var.secret_names.valkey_password}"
    identity            = var.workloads.valkey.identity_id
  }

  ingress {
    external_enabled = false
    target_port      = 6379
    transport        = "tcp"

    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  template {
    min_replicas = 1
    max_replicas = 1

    container {
      name    = "valkey"
      image   = var.workloads.valkey.image
      cpu     = var.valkey_cpu
      memory  = var.valkey_memory
      command = ["/bin/sh"]
      args = [
        "-c",
        "exec valkey-server --appendonly yes --appendfsync everysec --maxmemory ${var.valkey_maxmemory} --maxmemory-policy noeviction --requirepass \"$VALKEY_PASSWORD\"",
      ]

      env {
        name        = "VALKEY_PASSWORD"
        secret_name = "valkey-password"
      }

      volume_mounts {
        name = "valkey-data"
        path = "/data"
      }

      startup_probe {
        transport               = "TCP"
        port                    = 6379
        interval_seconds        = 10
        timeout                 = 5
        failure_count_threshold = 30
      }

      liveness_probe {
        transport               = "TCP"
        port                    = 6379
        interval_seconds        = 30
        timeout                 = 5
        failure_count_threshold = 3
      }

      readiness_probe {
        transport               = "TCP"
        port                    = 6379
        interval_seconds        = 10
        timeout                 = 5
        failure_count_threshold = 3
        success_count_threshold = 1
      }
    }

    volume {
      name         = "valkey-data"
      storage_name = local.valkey_storage_name
      storage_type = "NfsAzureFile"
    }
  }

  tags       = var.tags
  depends_on = [azapi_resource.valkey_environment_storage]
}
