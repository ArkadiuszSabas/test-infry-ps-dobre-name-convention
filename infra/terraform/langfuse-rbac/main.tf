locals {
  app_token         = lower(replace(var.app_id, "/[^0-9A-Za-z]/", ""))
  environment_token = lower(replace(var.environment, "/[^0-9A-Za-z]/", ""))
  instance_token    = lower(replace(var.instance_number, "/[^0-9A-Za-z]/", ""))
  workload_identity_names = {
    web        = "id-${local.app_token}-${local.environment_token}-langfuse-web-${local.instance_token}"
    worker     = "id-${local.app_token}-${local.environment_token}-langfuse-worker-${local.instance_token}"
    clickhouse = "id-${local.app_token}-${local.environment_token}-langfuse-clickhouse-${local.instance_token}"
    postgres   = "id-${local.app_token}-${local.environment_token}-langfuse-postgres-${local.instance_token}"
    valkey     = "id-${local.app_token}-${local.environment_token}-langfuse-valkey-${local.instance_token}"
  }
  namespace = "6ba7b811-9dad-11d1-80b4-00c04fd430c8"
  identities = merge({
    web        = data.azurerm_user_assigned_identity.workloads["web"].principal_id
    worker     = data.azurerm_user_assigned_identity.workloads["worker"].principal_id
    clickhouse = data.azurerm_user_assigned_identity.workloads["clickhouse"].principal_id
    postgres   = data.azurerm_user_assigned_identity.workloads["postgres"].principal_id
    valkey     = data.azurerm_user_assigned_identity.workloads["valkey"].principal_id
  }, { llmmagic = data.azurerm_user_assigned_identity.llmmagic.principal_id })
  secret_access = {
    web        = values(var.secret_names)
    worker     = [var.secret_names.clickhouse_password, var.secret_names.encryption_key, var.secret_names.postgres_password, var.secret_names.salt, var.secret_names.valkey_password]
    clickhouse = [var.secret_names.clickhouse_password]
    postgres   = [var.secret_names.postgres_password]
    valkey     = [var.secret_names.valkey_password]
    llmmagic   = [var.secret_names.init_project_public_key, var.secret_names.init_project_secret_key]
  }
  secret_assignments = merge([
    for workload, secret_names in local.secret_access : {
      for secret_name in secret_names : "${workload}-${secret_name}" => { principal_id = local.identities[workload], secret_name = secret_name }
    }
  ]...)
}

data "azurerm_container_registry" "this" {
  name                = var.container_registry_name
  resource_group_name = var.application_resource_group_name
}

data "azurerm_key_vault" "this" {
  name                = var.key_vault_name
  resource_group_name = var.application_resource_group_name
}

data "azurerm_user_assigned_identity" "llmmagic" {
  name                = var.llmmagic_identity_name
  resource_group_name = var.application_resource_group_name
}
data "azurerm_user_assigned_identity" "workloads" {
  for_each            = local.workload_identity_names
  name                = each.value
  resource_group_name = var.application_resource_group_name
}

resource "azurerm_role_assignment" "acr_pull" {
  for_each                         = { for key, principal_id in local.identities : key => principal_id if key != "llmmagic" }
  name                             = uuidv5(local.namespace, lower(join("|", [data.azurerm_container_registry.this.id, "AcrPull", each.value, "", "true"])))
  scope                            = data.azurerm_container_registry.this.id
  role_definition_name             = "AcrPull"
  principal_id                     = each.value
  principal_type                   = "ServicePrincipal"
  skip_service_principal_aad_check = true
}

resource "azurerm_role_assignment" "key_vault_secrets_user" {
  for_each                         = local.secret_assignments
  name                             = uuidv5(local.namespace, lower(join("|", ["${data.azurerm_key_vault.this.id}/secrets/${each.value.secret_name}", "Key Vault Secrets User", each.value.principal_id, "", "true"])))
  scope                            = "${data.azurerm_key_vault.this.id}/secrets/${each.value.secret_name}"
  role_definition_name             = "Key Vault Secrets User"
  principal_id                     = each.value.principal_id
  principal_type                   = "ServicePrincipal"
  skip_service_principal_aad_check = true
}
