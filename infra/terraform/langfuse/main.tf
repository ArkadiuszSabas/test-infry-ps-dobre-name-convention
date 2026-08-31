locals {
  role_assignment_namespace = "6ba7b811-9dad-11d1-80b4-00c04fd430c8"
  acr_pull_role_name        = "AcrPull"
  key_vault_secrets_role    = "Key Vault Secrets User"

  workload_identity_names = {
    langfuse-web        = var.workload_identity_names.web
    langfuse-worker     = var.workload_identity_names.worker
    langfuse-clickhouse = var.workload_identity_names.clickhouse
    langfuse-postgres   = var.workload_identity_names.postgres
    langfuse-valkey     = var.workload_identity_names.valkey
  }

  langfuse_principal_ids = merge(module.managed_identities.principal_ids, {
    llmmagic = data.azurerm_user_assigned_identity.llmmagic.principal_id
  })

  workload_secret_access = {
    langfuse-web = {
      clickhouse-password = var.secret_names.clickhouse_password
      encryption-key      = var.secret_names.encryption_key
      init-public-key     = var.secret_names.init_project_public_key
      init-secret-key     = var.secret_names.init_project_secret_key
      nextauth-secret     = var.secret_names.nextauth_secret
      postgres-password   = var.secret_names.postgres_password
      salt                = var.secret_names.salt
      valkey-password     = var.secret_names.valkey_password
    }
    langfuse-worker = {
      clickhouse-password = var.secret_names.clickhouse_password
      encryption-key      = var.secret_names.encryption_key
      postgres-password   = var.secret_names.postgres_password
      salt                = var.secret_names.salt
      valkey-password     = var.secret_names.valkey_password
    }
    langfuse-clickhouse = {
      clickhouse-password = var.secret_names.clickhouse_password
    }
    langfuse-postgres = {
      postgres-password = var.secret_names.postgres_password
    }
    langfuse-valkey = {
      valkey-password = var.secret_names.valkey_password
    }
    llmmagic = {
      init-public-key = var.secret_names.init_project_public_key
      init-secret-key = var.secret_names.init_project_secret_key
    }
  }

  key_vault_secret_role_assignments = merge([
    for workload, secrets in local.workload_secret_access : {
      for secret_key, secret_name in secrets :
      "${workload}-${secret_key}" => {
        principal_id = local.langfuse_principal_ids[workload]
        secret_name  = secret_name
      }
    }
  ]...)
}

data "azurerm_resource_group" "application" {
  name = var.application_resource_group_name
}

data "azurerm_resource_group" "network" {
  name = var.network_resource_group_name
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

data "azurerm_user_assigned_identity" "llmmagic" {
  name                = var.llmmagic_identity_name
  resource_group_name = data.azurerm_resource_group.application.name
}

data "azurerm_virtual_network" "shared" {
  name                = var.resource_names.virtual_network
  resource_group_name = data.azurerm_resource_group.network.name
}

data "azurerm_subnet" "private_endpoints" {
  name                 = var.resource_names.private_endpoint_subnet
  virtual_network_name = data.azurerm_virtual_network.shared.name
  resource_group_name  = data.azurerm_resource_group.network.name
}

data "azurerm_private_dns_zone" "storage_blob" {
  provider = azurerm.hub

  name                = var.resource_names.storage_blob_private_dns_zone
  resource_group_name = var.private_dns_resource_group_name
}

data "azurerm_private_dns_zone" "storage_file" {
  provider = azurerm.hub

  name                = var.resource_names.storage_file_private_dns_zone
  resource_group_name = var.private_dns_resource_group_name
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

resource "azurerm_role_assignment" "acr_pull" {
  for_each = module.managed_identities.principal_ids

  name = uuidv5(local.role_assignment_namespace, lower(join("|", [
    data.azurerm_container_registry.shared.id,
    local.acr_pull_role_name,
    each.value,
    "",
    "true",
  ])))

  scope                            = data.azurerm_container_registry.shared.id
  role_definition_name             = local.acr_pull_role_name
  principal_id                     = each.value
  principal_type                   = "ServicePrincipal"
  skip_service_principal_aad_check = true
}

resource "azurerm_role_assignment" "key_vault_secrets_user" {
  for_each = local.key_vault_secret_role_assignments

  name = uuidv5(local.role_assignment_namespace, lower(join("|", [
    "${data.azurerm_key_vault.shared.id}/secrets/${each.value.secret_name}",
    local.key_vault_secrets_role,
    each.value.principal_id,
    "",
    "true",
  ])))

  scope                            = "${data.azurerm_key_vault.shared.id}/secrets/${each.value.secret_name}"
  role_definition_name             = local.key_vault_secrets_role
  principal_id                     = each.value.principal_id
  principal_type                   = "ServicePrincipal"
  skip_service_principal_aad_check = true
}

resource "time_sleep" "acr_pull_propagation" {
  for_each = azurerm_role_assignment.acr_pull

  create_duration = "180s"

  lifecycle {
    replace_triggered_by = [azurerm_role_assignment.acr_pull[each.key]]
  }
}

resource "time_sleep" "key_vault_role_propagation" {
  for_each = azurerm_role_assignment.key_vault_secrets_user

  create_duration = "180s"

  lifecycle {
    replace_triggered_by = [azurerm_role_assignment.key_vault_secrets_user[each.key]]
  }
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
  storage_account_name                     = var.resource_names.langfuse_storage_account
  clickhouse_storage_account_name          = var.resource_names.langfuse_files_storage_account
  private_endpoint_subnet_id               = data.azurerm_subnet.private_endpoints.id
  storage_blob_private_dns_zone_id         = data.azurerm_private_dns_zone.storage_blob.id
  storage_file_private_dns_zone_id         = data.azurerm_private_dns_zone.storage_file.id
  key_vault_uri                            = data.azurerm_key_vault.shared.vault_uri
  secret_names                             = var.secret_names
  workloads = {
    web = {
      name               = var.resource_names.langfuse_web
      image              = "${data.azurerm_container_registry.shared.login_server}/langfuse/langfuse:${var.langfuse_version}"
      identity_id        = module.managed_identities.ids["langfuse-web"]
      identity_client_id = module.managed_identities.client_ids["langfuse-web"]
    }
    worker = {
      name               = var.resource_names.langfuse_worker
      image              = "${data.azurerm_container_registry.shared.login_server}/langfuse/worker:${var.langfuse_version}"
      identity_id        = module.managed_identities.ids["langfuse-worker"]
      identity_client_id = module.managed_identities.client_ids["langfuse-worker"]
    }
    clickhouse = {
      name               = var.resource_names.langfuse_clickhouse
      image              = "${data.azurerm_container_registry.shared.login_server}/langfuse/clickhouse:${var.clickhouse_version}"
      identity_id        = module.managed_identities.ids["langfuse-clickhouse"]
      identity_client_id = module.managed_identities.client_ids["langfuse-clickhouse"]
    }
    postgres = {
      name               = var.resource_names.langfuse_postgres
      image              = "${data.azurerm_container_registry.shared.login_server}/langfuse/postgres:${var.postgres_version}"
      identity_id        = module.managed_identities.ids["langfuse-postgres"]
      identity_client_id = module.managed_identities.client_ids["langfuse-postgres"]
    }
    valkey = {
      name               = var.resource_names.langfuse_valkey
      image              = "${data.azurerm_container_registry.shared.login_server}/langfuse/valkey:${var.valkey_version}"
      identity_id        = module.managed_identities.ids["langfuse-valkey"]
      identity_client_id = module.managed_identities.client_ids["langfuse-valkey"]
    }
  }
  tags = var.tags

  depends_on = [
    time_sleep.acr_pull_propagation,
    time_sleep.key_vault_role_propagation,
  ]
}
