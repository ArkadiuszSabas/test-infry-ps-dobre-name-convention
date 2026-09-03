data "azurerm_client_config" "current" {}

data "azurerm_resource_group" "environment" {
  name = var.application_resource_group_name
}

data "azurerm_subnet" "container_apps_infrastructure" {
  name                 = var.container_apps_infrastructure_subnet_name
  virtual_network_name = var.virtual_network_name
  resource_group_name  = var.network_resource_group_name
}

resource "terraform_data" "approved_design_guard" {
  lifecycle {
    precondition {
      condition     = var.security_design_approved && var.resource_provider_list_verified
      error_message = "ProService security design and authoritative Resource Provider list must be approved before planning this root."
    }

    precondition {
      condition = (
        length(var.container_apps) == 0 &&
        length(var.dapr_components) == 0 &&
        length(var.container_app_jobs) == 0
      ) || var.runtime_dependencies_ready
      error_message = "Runtime workloads require runtime_dependencies_ready=true after network completion and RBAC apply."
    }

    precondition {
      condition = startswith(
        lower(data.azurerm_subnet.container_apps_infrastructure.id),
        lower("/subscriptions/${var.subscription_id}/resourceGroups/${var.network_resource_group_name}/providers/Microsoft.Network/virtualNetworks/"),
      )
      error_message = "Container Apps infrastructure subnet must belong to the target subscription and network resource group."
    }

    precondition {
      condition = length(var.container_apps) == 0 || try(
        var.dapr_components["servicebus-pubsub-api"].component_type == "pubsub.azure.servicebus.queues" &&
        var.dapr_components["servicebus-pubsub-api"].name == "docmind-servicebus-pubsub-api" &&
        var.dapr_components["servicebus-pubsub-api"].managed_identity_key == "dapr-servicebus-api" &&
        var.dapr_components["servicebus-pubsub-api"].service_bus_metadata_enabled &&
        var.dapr_components["servicebus-pubsub-worker"].component_type == "pubsub.azure.servicebus.queues" &&
        var.dapr_components["servicebus-pubsub-worker"].name == "docmind-servicebus-pubsub-worker" &&
        var.dapr_components["servicebus-pubsub-worker"].managed_identity_key == "dapr-servicebus-worker" &&
        var.dapr_components["servicebus-pubsub-worker"].service_bus_metadata_enabled &&
        var.dapr_components["servicebus-pubsub-llmmagic"].component_type == "pubsub.azure.servicebus.queues" &&
        var.dapr_components["servicebus-pubsub-llmmagic"].name == "docmind-servicebus-pubsub-llmmagic" &&
        var.dapr_components["servicebus-pubsub-llmmagic"].managed_identity_key == "dapr-servicebus-llmmagic" &&
        var.dapr_components["servicebus-pubsub-llmmagic"].service_bus_metadata_enabled,
        false,
      )
      error_message = "A runtime core configuration must retain the API, Worker, and LLM Magic Service Bus Dapr components with their dedicated managed identities and application component names."
    }

    precondition {
      condition = length(var.container_apps) == 0 || try(
        var.container_app_jobs["api-migrations"].identity_key == "api-migrator" &&
        var.container_app_jobs["api-migrations"].registry_identity_key == "api-migrator" &&
        contains(
          var.container_app_jobs["api-migrations"].args,
          "/usr/local/lib/python3.14/site-packages/docmind_api/bootstrap/commands/apply_migrations.py",
        ),
        false,
      )
      error_message = "A runtime core configuration must retain the api-migrations Container Apps job and its dedicated managed identity."
    }
  }
}

locals {
  tenant_token      = lower(replace(var.tenant_prefix, "/[^0-9A-Za-z]/", ""))
  app_token         = lower(replace(var.app_id, "/[^0-9A-Za-z]/", ""))
  environment_token = lower(replace(var.environment, "/[^0-9A-Za-z]/", ""))
  instance_token    = lower(replace(var.instance_number, "/[^0-9A-Za-z]/", ""))

  resource_names = {
    key_vault                  = "${local.tenant_token}kv${local.app_token}app${local.environment_token}${local.instance_token}"
    storage_account            = "${local.tenant_token}st${local.app_token}doc${local.environment_token}${local.instance_token}"
    container_registry         = "${local.tenant_token}cr${local.app_token}${local.environment_token}${local.instance_token}"
    log_analytics              = "log-${local.app_token}-${local.environment_token}-${local.instance_token}"
    application_insights       = "appi-${local.app_token}-${local.environment_token}-${local.instance_token}"
    service_bus                = "${local.tenant_token}sbns${local.app_token}${local.environment_token}${local.instance_token}"
    document_intelligence      = "${local.tenant_token}di${local.app_token}${local.environment_token}${local.instance_token}"
    foundry_account            = "ais-${local.app_token}-${local.environment_token}-${local.instance_token}"
    foundry_project            = "proj-${local.app_token}-${local.environment_token}-${local.instance_token}"
    container_apps_environment = "cae-${local.app_token}-${local.environment_token}-${local.instance_token}"
    postgresql                 = "psql-${local.app_token}-${local.environment_token}-${local.instance_token}"
  }

  workload_identities = {
    for workload in var.workload_identity_workloads : workload => {
      name = "id-${local.app_token}-${local.environment_token}-${workload}-${local.instance_token}"
    }
  }

  service_bus_queues = {
    "document-processing" = {
      dead_lettering_on_message_expiration = true
      default_message_ttl                  = "P14D"
      lock_duration                        = "PT1M"
      max_delivery_count                   = 10
      max_size_in_megabytes                = 1024
    }
    "processing-results" = {
      dead_lettering_on_message_expiration = true
      default_message_ttl                  = "P14D"
      lock_duration                        = "PT1M"
      max_delivery_count                   = 10
      max_size_in_megabytes                = 1024
    }
  }

  postgresql_database_names = toset([
    coalesce(
      var.postgresql_database_name,
      "db-${local.app_token}-${local.environment_token}-app",
    ),
  ])

  gpt_deployment = merge(var.gpt_deployment, {
    name = "dep-${local.app_token}-${local.environment_token}-gpt55-${local.instance_token}"
  })

  container_app_job_workloads = {
    "api-migrations" = "api-migrate"
  }

  cmk_identities = {
    "cmk-document-intelligence" = { name = "id-${local.app_token}-${local.environment_token}-cmk-document-intelligence-${local.instance_token}" }
    "cmk-postgresql"            = { name = "id-${local.app_token}-${local.environment_token}-cmk-postgresql-${local.instance_token}" }
    "cmk-storage"               = { name = "id-${local.app_token}-${local.environment_token}-cmk-storage-${local.instance_token}" }
  }

  container_apps = {
    for key, app in var.container_apps : key => {
      name                  = "ca-${local.app_token}-${local.environment_token}-${key}-${local.instance_token}"
      container_name        = app.container_name
      image                 = app.image
      target_port           = app.target_port
      external_enabled      = app.external_enabled
      transport             = app.transport
      cpu                   = app.cpu
      memory                = app.memory
      min_replicas          = app.min_replicas
      max_replicas          = app.max_replicas
      identity_id           = module.managed_identities.ids[app.identity_key]
      identity_client_id    = module.managed_identities.client_ids[app.identity_key]
      extra_identity_ids    = toset([for identity_key in app.extra_identity_keys : module.managed_identities.ids[identity_key]])
      environment_variables = app.environment_variables
      health_probes         = app.health_probes
      dapr                  = app.dapr
      key_vault_secrets = {
        for secret_key, secret in app.key_vault_secrets : secret_key => {
          key_vault_secret_id = secret.key_vault_secret_id
          identity_id         = secret.identity_key == null ? null : module.managed_identities.ids[secret.identity_key]
        }
      }
      secret_environment_variables = app.secret_environment_variables
      custom_scale_rules = {
        for rule_key, rule in app.custom_scale_rules : rule_key => {
          custom_rule_type = rule.custom_rule_type
          metadata         = rule.metadata
          identity_id      = rule.identity_key == null ? null : module.managed_identities.ids[rule.identity_key]
        }
      }
    }
  }

  dapr_components = {
    for key, component in var.dapr_components : key => {
      name           = component.name
      component_type = component.component_type
      version        = component.version
      ignore_errors  = component.ignore_errors
      init_timeout   = component.init_timeout
      scopes         = component.scopes
      metadata = merge(
        component.metadata,
        component.managed_identity_key == null ? {} : {
          azureClientId = module.managed_identities.client_ids[component.managed_identity_key]
        },
        component.service_bus_metadata_enabled ? {
          disableEntityManagement = "true"
          namespaceName           = "${azurerm_servicebus_namespace.this.name}.servicebus.windows.net"
        } : {},
      )
    }
  }

  container_app_jobs = {
    for key, job in var.container_app_jobs : key => {
      name                       = "caj-${local.app_token}-${local.environment_token}-${local.container_app_job_workloads[key]}-${local.instance_token}"
      container_name             = job.container_name
      image                      = job.image
      command                    = job.command
      args                       = job.args
      cpu                        = job.cpu
      memory                     = job.memory
      replica_timeout_in_seconds = job.replica_timeout_in_seconds
      replica_retry_limit        = job.replica_retry_limit
      parallelism                = job.parallelism
      replica_completion_count   = job.replica_completion_count
      identity_id                = module.managed_identities.ids[job.identity_key]
      identity_client_id         = module.managed_identities.client_ids[job.identity_key]
      registry_identity_id       = module.managed_identities.ids[job.registry_identity_key]
      environment_variables      = job.environment_variables
      key_vault_secrets = {
        for secret_key, secret in job.key_vault_secrets : secret_key => {
          key_vault_secret_id = secret.key_vault_secret_id
          identity_id         = secret.identity_key == null ? null : module.managed_identities.ids[secret.identity_key]
        }
      }
      secret_environment_variables = job.secret_environment_variables
    }
  }
}

module "managed_identities" {
  source = "../modules/managed-identities"

  location            = var.location
  resource_group_name = data.azurerm_resource_group.environment.name
  identities          = local.workload_identities
  tags                = var.tags

  depends_on = [terraform_data.approved_design_guard]
}

# CMK identities are owned and created by the separate uami-cmk root. Core only
# reads them so it can attach them to the CMK-enabled Azure resources.
data "azurerm_user_assigned_identity" "cmk" {
  for_each = local.cmk_identities

  name                = each.value.name
  resource_group_name = data.azurerm_resource_group.environment.name
}

module "key_vault" {
  source = "../modules/key-vault"

  name                          = local.resource_names.key_vault
  location                      = var.location
  resource_group_name           = data.azurerm_resource_group.environment.name
  tenant_id                     = data.azurerm_client_config.current.tenant_id
  secrets_user_principal_ids    = {}
  secrets_officer_principal_ids = {}
  public_network_access_enabled = false
  network_acls_default_action   = "Deny"
  network_acls_bypass           = "None"
  purge_protection_enabled      = true
  soft_delete_retention_days    = 90
  tags                          = var.tags
}

module "storage" {
  source = "../modules/storage"

  name                              = local.resource_names.storage_account
  location                          = var.location
  resource_group_name               = data.azurerm_resource_group.environment.name
  replication_type                  = var.environment == "prd" ? "GRS" : "LRS"
  containers                        = var.storage_containers
  blob_data_contributor_assignments = {}
  shared_access_key_enabled         = false
  default_to_oauth_authentication   = true
  public_network_access_enabled     = false
  cmk_key_vault_key_id              = var.cmk.storage_key_id
  cmk_user_assigned_identity_id     = data.azurerm_user_assigned_identity.cmk["cmk-storage"].id
  tags                              = var.tags
}

module "container_registry" {
  source = "../modules/container-registry"

  name                = local.resource_names.container_registry
  location            = var.location
  resource_group_name = data.azurerm_resource_group.environment.name
  sku                 = "Premium"
  pull_principal_ids  = {}
  push_principal_ids  = {}
  tags                = var.tags
}

module "observability" {
  source = "../modules/observability"

  log_analytics_workspace_name = local.resource_names.log_analytics
  application_insights_name    = local.resource_names.application_insights
  location                     = var.location
  resource_group_name          = data.azurerm_resource_group.environment.name
  retention_in_days            = var.environment == "prd" ? 90 : 30
  tags                         = var.tags
}

resource "azurerm_servicebus_namespace" "this" {
  name                          = local.resource_names.service_bus
  location                      = var.location
  resource_group_name           = data.azurerm_resource_group.environment.name
  sku                           = "Premium"
  capacity                      = 1
  premium_messaging_partitions  = 1
  local_auth_enabled            = false
  minimum_tls_version           = "1.2"
  public_network_access_enabled = false

  tags = var.tags
}

resource "azurerm_servicebus_queue" "this" {
  for_each = local.service_bus_queues

  name                                 = each.key
  namespace_id                         = azurerm_servicebus_namespace.this.id
  dead_lettering_on_message_expiration = each.value.dead_lettering_on_message_expiration
  default_message_ttl                  = each.value.default_message_ttl
  lock_duration                        = each.value.lock_duration
  max_delivery_count                   = each.value.max_delivery_count
  max_size_in_megabytes                = each.value.max_size_in_megabytes
  partitioning_enabled                 = false
}

module "ai_services" {
  source = "../modules/ai-services"

  foundry_enabled                                     = var.foundry_enabled
  document_intelligence_name                          = local.resource_names.document_intelligence
  document_intelligence_sku_name                      = "S0"
  foundry_account_name                                = local.resource_names.foundry_account
  foundry_sku_name                                    = "S0"
  foundry_project_name                                = local.resource_names.foundry_project
  foundry_project_display_name                        = "DocMind.Ai ${upper(var.environment)}"
  foundry_project_description                         = "DocMind.Ai ${var.environment} AI project."
  gpt_deployment                                      = local.gpt_deployment
  location                                            = var.location
  document_intelligence_location                      = var.location
  resource_group_name                                 = data.azurerm_resource_group.environment.name
  public_network_access_enabled                       = false
  document_intelligence_public_network_access_enabled = false
  network_acls_default_action                         = "Deny"
  document_intelligence_network_acls_ip_rules         = []
  document_intelligence_user_principal_ids            = {}
  foundry_user_principal_ids                          = {}
  foundry_openai_user_principal_ids                   = {}
  document_intelligence_cmk_key_vault_key_id          = var.cmk.document_intelligence_key_id
  document_intelligence_cmk_identity_id               = data.azurerm_user_assigned_identity.cmk["cmk-document-intelligence"].id
  document_intelligence_cmk_identity_client_id        = data.azurerm_user_assigned_identity.cmk["cmk-document-intelligence"].client_id
  tags                                                = var.tags
}


module "postgresql" {
  source = "../modules/postgresql"

  name                          = local.resource_names.postgresql
  location                      = var.location
  resource_group_name           = data.azurerm_resource_group.environment.name
  tenant_id                     = data.azurerm_client_config.current.tenant_id
  postgresql_version            = "16"
  sku_name                      = var.environment == "prd" ? "GP_Standard_D2s_v3" : "B_Standard_B2s"
  zone                          = "1"
  storage_mb                    = var.environment == "prd" ? 65536 : 32768
  backup_retention_days         = var.environment == "prd" ? 35 : 7
  geo_redundant_backup_enabled  = var.environment == "prd"
  database_names                = local.postgresql_database_names
  firewall_ip_addresses         = []
  public_network_access_enabled = false
  cmk_key_vault_key_id          = var.cmk.postgresql_key_id
  cmk_user_assigned_identity_id = data.azurerm_user_assigned_identity.cmk["cmk-postgresql"].id
  active_directory_administrator = {
    object_id      = module.managed_identities.principal_ids["api-migrator"]
    principal_name = local.workload_identities["api-migrator"].name
    principal_type = "ServicePrincipal"
  }
  tags = var.tags
}

module "container_apps" {
  source = "../modules/container-apps"

  environment_name           = local.resource_names.container_apps_environment
  location                   = var.location
  resource_group_name        = data.azurerm_resource_group.environment.name
  log_analytics_workspace_id = module.observability.log_analytics_workspace_id
  infrastructure_subnet_id   = data.azurerm_subnet.container_apps_infrastructure.id
  public_network_access      = "Disabled"
  app_environment            = var.environment
  registry_server            = module.container_registry.login_server
  workload_profiles = {
    langfuse-e4 = {
      workload_profile_type = "E4"
      minimum_count         = 0
      maximum_count         = 1
    }
  }
  apps            = local.container_apps
  dapr_components = local.dapr_components
  jobs            = local.container_app_jobs
  tags            = var.tags
}
