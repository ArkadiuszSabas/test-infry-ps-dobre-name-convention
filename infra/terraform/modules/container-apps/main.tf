resource "azurerm_container_app_environment" "this" {
  name                               = var.environment_name
  location                           = var.location
  resource_group_name                = var.resource_group_name
  infrastructure_resource_group_name = "ME_${var.environment_name}_${var.resource_group_name}_${var.location}"

  log_analytics_workspace_id = var.log_analytics_workspace_id
  logs_destination           = "log-analytics"
  infrastructure_subnet_id   = var.infrastructure_subnet_id
  public_network_access      = var.public_network_access

  workload_profile {
    name                  = "Consumption"
    workload_profile_type = "Consumption"
    minimum_count         = 0
    maximum_count         = 0
  }

  dynamic "workload_profile" {
    for_each = var.workload_profiles

    content {
      name                  = workload_profile.key
      workload_profile_type = workload_profile.value.workload_profile_type
      minimum_count         = workload_profile.value.minimum_count
      maximum_count         = workload_profile.value.maximum_count
    }
  }

  tags = var.tags
}

locals {
  app_ingress_origins = {
    for key, app in var.apps : key => "https://${app.name}.${app.external_enabled ? "" : "internal."}${azurerm_container_app_environment.this.default_domain}"
  }
}

resource "azurerm_container_app" "this" {
  for_each = var.apps

  name                         = each.value.name
  container_app_environment_id = azurerm_container_app_environment.this.id
  resource_group_name          = var.resource_group_name
  revision_mode                = "Single"
  workload_profile_name        = "Consumption"

  identity {
    type         = "UserAssigned"
    identity_ids = sort(tolist(setunion(toset([each.value.identity_id]), each.value.extra_identity_ids)))
  }

  registry {
    server   = var.registry_server
    identity = each.value.identity_id
  }

  dynamic "secret" {
    for_each = each.value.key_vault_secrets

    content {
      name                = secret.key
      key_vault_secret_id = secret.value.key_vault_secret_id
      identity            = coalesce(secret.value.identity_id, each.value.identity_id)
    }
  }

  ingress {
    allow_insecure_connections = false
    external_enabled           = each.value.external_enabled
    target_port                = each.value.target_port
    transport                  = each.value.transport

    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  dynamic "dapr" {
    for_each = each.value.dapr == null ? [] : [each.value.dapr]

    content {
      app_id       = dapr.value.app_id
      app_port     = dapr.value.app_port
      app_protocol = dapr.value.app_protocol
    }
  }

  template {
    min_replicas               = each.value.min_replicas
    max_replicas               = each.value.max_replicas
    cooldown_period_in_seconds = var.scale_cooldown_period_in_seconds

    dynamic "custom_scale_rule" {
      for_each = each.value.custom_scale_rules

      content {
        name             = custom_scale_rule.key
        custom_rule_type = custom_scale_rule.value.custom_rule_type
        metadata         = custom_scale_rule.value.metadata
        identity_id      = custom_scale_rule.value.identity_id
      }
    }

    container {
      name   = each.value.container_name
      image  = each.value.image
      cpu    = each.value.cpu
      memory = each.value.memory

      dynamic "env" {
        for_each = merge(
          {
            APP_ENVIRONMENT     = var.app_environment
            DOCMIND_ENVIRONMENT = var.app_environment
            AZURE_CLIENT_ID     = each.value.identity_client_id
          },
          each.value.environment_variables,
          each.key == "api" && contains(keys(var.apps), "web") ? {
            DOCMIND_API_ALLOWED_WEB_ORIGINS = join(",", distinct([
              trimsuffix(coalesce(var.web_public_origin, local.app_ingress_origins["web"]), "/"),
              trimsuffix(local.app_ingress_origins["web"], "/"),
            ]))
          } : {},
          each.key == "web" && contains(keys(var.apps), "api") ? {
            DOCMIND_API_INTERNAL_BASE_URL         = local.app_ingress_origins["api"]
            DOCMIND_API_PROXY_UPSTREAM_TIMEOUT_MS = tostring(var.web_api_proxy_upstream_timeout_ms)
          } : {}
        )

        content {
          name  = env.key
          value = env.value
        }
      }

      dynamic "env" {
        for_each = each.value.secret_environment_variables

        content {
          name        = env.key
          secret_name = env.value
        }
      }
    }
  }

  tags = var.tags

  lifecycle {
    ignore_changes = [
      template[0].container[0].image,
    ]
  }

  depends_on = [
    azurerm_container_app_environment_dapr_component.this,
  ]
}

resource "azurerm_container_app_environment_dapr_component" "this" {
  for_each = var.dapr_components

  name                         = each.value.name
  container_app_environment_id = azurerm_container_app_environment.this.id
  component_type               = each.value.component_type
  version                      = each.value.version
  ignore_errors                = each.value.ignore_errors
  init_timeout                 = each.value.init_timeout
  scopes                       = sort(tolist(each.value.scopes))

  dynamic "metadata" {
    for_each = each.value.metadata

    content {
      name  = metadata.key
      value = metadata.value
    }
  }
}

resource "azurerm_container_app_job" "this" {
  for_each = var.jobs

  name                         = each.value.name
  location                     = var.location
  resource_group_name          = var.resource_group_name
  container_app_environment_id = azurerm_container_app_environment.this.id
  workload_profile_name        = "Consumption"

  replica_timeout_in_seconds = each.value.replica_timeout_in_seconds
  replica_retry_limit        = each.value.replica_retry_limit

  identity {
    type         = "UserAssigned"
    identity_ids = [each.value.identity_id]
  }

  registry {
    server   = var.registry_server
    identity = each.value.registry_identity_id
  }

  dynamic "secret" {
    for_each = each.value.key_vault_secrets

    content {
      name                = secret.key
      key_vault_secret_id = secret.value.key_vault_secret_id
      identity            = coalesce(secret.value.identity_id, each.value.identity_id)
    }
  }

  manual_trigger_config {
    parallelism              = each.value.parallelism
    replica_completion_count = each.value.replica_completion_count
  }

  template {
    container {
      name    = each.value.container_name
      image   = each.value.image
      command = each.value.command
      args    = each.value.args
      cpu     = each.value.cpu
      memory  = each.value.memory

      dynamic "env" {
        for_each = merge(
          {
            APP_ENVIRONMENT     = var.app_environment
            DOCMIND_ENVIRONMENT = var.app_environment
            AZURE_CLIENT_ID     = each.value.identity_client_id
          },
          each.value.environment_variables
        )

        content {
          name  = env.key
          value = env.value
        }
      }

      dynamic "env" {
        for_each = each.value.secret_environment_variables

        content {
          name        = env.key
          secret_name = env.value
        }
      }
    }
  }

  tags = var.tags

  lifecycle {
    ignore_changes = [
      template[0].container[0].image,
    ]
  }
}
