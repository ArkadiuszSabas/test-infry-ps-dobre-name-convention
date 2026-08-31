locals {
  tenant_token                        = lower(replace(var.tenant_prefix, "/[^0-9A-Za-z]/", ""))
  app_token                           = lower(replace(var.app_id, "/[^0-9A-Za-z]/", ""))
  environment_token                   = lower(replace(var.environment, "/[^0-9A-Za-z]/", ""))
  instance_token                      = lower(replace(var.instance_number, "/[^0-9A-Za-z]/", ""))
  langfuse_storage_account_name       = "${local.tenant_token}st${local.app_token}lfblob${local.environment_token}${local.instance_token}"
  langfuse_files_storage_account_name = "${local.tenant_token}st${local.app_token}lffile${local.environment_token}${local.instance_token}"
  langfuse_container_app_names = {
    web        = "ca-${local.app_token}-${local.environment_token}-langfuse-web-${local.instance_token}"
    worker     = "ca-${local.app_token}-${local.environment_token}-langfuse-worker-${local.instance_token}"
    clickhouse = "ca-${local.app_token}-${local.environment_token}-langfuse-clickhouse-${local.instance_token}"
    postgres   = "ca-${local.app_token}-${local.environment_token}-langfuse-postgres-${local.instance_token}"
    valkey     = "ca-${local.app_token}-${local.environment_token}-langfuse-valkey-${local.instance_token}"
  }
  workload_identity_names = {
    langfuse-web        = "id-${local.app_token}-${local.environment_token}-langfuse-web-${local.instance_token}"
    langfuse-worker     = "id-${local.app_token}-${local.environment_token}-langfuse-worker-${local.instance_token}"
    langfuse-clickhouse = "id-${local.app_token}-${local.environment_token}-langfuse-clickhouse-${local.instance_token}"
    langfuse-postgres   = "id-${local.app_token}-${local.environment_token}-langfuse-postgres-${local.instance_token}"
    langfuse-valkey     = "id-${local.app_token}-${local.environment_token}-langfuse-valkey-${local.instance_token}"
  }
}

resource "terraform_data" "runtime_dependencies_guard" {
  lifecycle {
    precondition {
      condition     = !var.runtime_enabled || var.runtime_dependencies_ready
      error_message = "Set runtime_dependencies_ready=true only after Langfuse RBAC and Network Completion have succeeded."
    }
  }
}

data "azurerm_resource_group" "application" {
  name = var.application_resource_group_name
}

data "azurerm_container_app_environment" "shared" {
  name                = var.resource_names.container_apps_environment
  resource_group_name = data.azurerm_resource_group.application.name
}

data "azurerm_container_registry" "shared" {
  name                = var.resource_names.container_registry
  resource_group_name = data.azurerm_resource_group.application.name
}

data "azurerm_key_vault" "shared" {
  name                = var.resource_names.key_vault
  resource_group_name = data.azurerm_resource_group.application.name
}

module "managed_identities" {
  source = "../modules/managed-identities"

  location            = var.location
  resource_group_name = data.azurerm_resource_group.application.name
  identities = {
    for workload, name in local.workload_identity_names : workload => {
      name = name
    }
  }
  tags = var.tags
}

module "langfuse" {
  source = "../modules/langfuse"

  enabled     = true
  environment = var.environment
  private_access_enabled = (
    lower(data.azurerm_container_app_environment.shared.public_network_access) == "disabled"
  )
  location                                 = var.location
  resource_group_name                      = data.azurerm_resource_group.application.name
  container_app_environment_id             = data.azurerm_container_app_environment.shared.id
  container_app_environment_default_domain = data.azurerm_container_app_environment.shared.default_domain
  registry_server                          = data.azurerm_container_registry.shared.login_server
  storage_account_name                     = local.langfuse_storage_account_name
  clickhouse_storage_account_name          = local.langfuse_files_storage_account_name
  clickhouse_workload_profile_name         = "langfuse-e4"
  runtime_enabled                          = var.runtime_enabled
  create_private_endpoints                 = false
  key_vault_uri                            = data.azurerm_key_vault.shared.vault_uri
  secret_names                             = var.secret_names
  workloads = {
    web = {
      name               = local.langfuse_container_app_names.web
      image              = "${data.azurerm_container_registry.shared.login_server}/langfuse/langfuse:${var.langfuse_version}"
      identity_id        = module.managed_identities.ids["langfuse-web"]
      identity_client_id = module.managed_identities.client_ids["langfuse-web"]
    }
    worker = {
      name               = local.langfuse_container_app_names.worker
      image              = "${data.azurerm_container_registry.shared.login_server}/langfuse/worker:${var.langfuse_version}"
      identity_id        = module.managed_identities.ids["langfuse-worker"]
      identity_client_id = module.managed_identities.client_ids["langfuse-worker"]
    }
    clickhouse = {
      name               = local.langfuse_container_app_names.clickhouse
      image              = "${data.azurerm_container_registry.shared.login_server}/langfuse/clickhouse:${var.clickhouse_version}"
      identity_id        = module.managed_identities.ids["langfuse-clickhouse"]
      identity_client_id = module.managed_identities.client_ids["langfuse-clickhouse"]
    }
    postgres = {
      name               = local.langfuse_container_app_names.postgres
      image              = "${data.azurerm_container_registry.shared.login_server}/langfuse/postgres:${var.postgres_version}"
      identity_id        = module.managed_identities.ids["langfuse-postgres"]
      identity_client_id = module.managed_identities.client_ids["langfuse-postgres"]
    }
    valkey = {
      name               = local.langfuse_container_app_names.valkey
      image              = "${data.azurerm_container_registry.shared.login_server}/langfuse/valkey:${var.valkey_version}"
      identity_id        = module.managed_identities.ids["langfuse-valkey"]
      identity_client_id = module.managed_identities.client_ids["langfuse-valkey"]
    }
  }
  tags = var.tags

  depends_on = [terraform_data.runtime_dependencies_guard]
}
