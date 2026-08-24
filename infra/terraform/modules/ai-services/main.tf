resource "azurerm_cognitive_account" "document_intelligence" {
  name                = var.document_intelligence_name
  location            = var.document_intelligence_location
  resource_group_name = var.resource_group_name
  kind                = "FormRecognizer"
  sku_name            = var.document_intelligence_sku_name

  custom_subdomain_name         = var.document_intelligence_name
  local_auth_enabled            = false
  public_network_access_enabled = var.document_intelligence_public_network_access_enabled

  network_acls {
    default_action = var.network_acls_default_action
    ip_rules       = sort(tolist(var.document_intelligence_network_acls_ip_rules))
  }

  identity {
    type         = "SystemAssigned, UserAssigned"
    identity_ids = [var.document_intelligence_cmk_identity_id]
  }

  customer_managed_key {
    key_vault_key_id   = var.document_intelligence_cmk_key_vault_key_id
    identity_client_id = var.document_intelligence_cmk_identity_client_id
  }

  tags = var.tags
}

resource "azurerm_cognitive_account" "foundry" {
  count = var.foundry_enabled ? 1 : 0

  name                = var.foundry_account_name
  location            = var.location
  resource_group_name = var.resource_group_name
  kind                = "AIServices"
  sku_name            = var.foundry_sku_name

  custom_subdomain_name         = var.foundry_account_name
  local_auth_enabled            = false
  project_management_enabled    = true
  public_network_access_enabled = var.public_network_access_enabled

  network_acls {
    bypass         = "AzureServices"
    default_action = var.network_acls_default_action
  }

  identity {
    type         = var.foundry_cmk_enabled ? "SystemAssigned, UserAssigned" : "SystemAssigned"
    identity_ids = var.foundry_cmk_enabled ? [var.foundry_cmk_identity_id] : []
  }

  dynamic "customer_managed_key" {
    for_each = var.foundry_cmk_enabled ? [1] : []

    content {
      key_vault_key_id   = var.foundry_cmk_key_vault_key_id
      identity_client_id = var.foundry_cmk_identity_client_id
    }
  }

  tags = var.tags
}

resource "azurerm_cognitive_account_project" "foundry" {
  count = var.foundry_enabled ? 1 : 0

  name                 = var.foundry_project_name
  cognitive_account_id = azurerm_cognitive_account.foundry[0].id
  location             = var.location
  display_name         = var.foundry_project_display_name
  description          = var.foundry_project_description

  identity {
    type = "SystemAssigned"
  }

  tags = var.tags
}

resource "azurerm_cognitive_deployment" "gpt" {
  count = var.foundry_enabled ? 1 : 0

  name                 = var.gpt_deployment.name
  cognitive_account_id = azurerm_cognitive_account.foundry[0].id
  rai_policy_name      = "Microsoft.DefaultV2"

  dynamic_throttling_enabled = var.gpt_deployment.dynamic_throttling_enabled
  version_upgrade_option     = var.gpt_deployment.version_upgrade_option

  model {
    format  = var.gpt_deployment.model_format
    name    = var.gpt_deployment.model_name
    version = var.gpt_deployment.model_version
  }

  sku {
    name     = var.gpt_deployment.sku_name
    capacity = var.gpt_deployment.capacity
  }

  depends_on = [
    azurerm_cognitive_account_project.foundry
  ]
}

locals {
  role_assignment_uuid_namespace        = "6ba7b811-9dad-11d1-80b4-00c04fd430c8"
  cognitive_user_role_definition        = "Cognitive Services User"
  cognitive_openai_user_role_definition = "Cognitive Services OpenAI User"
}

resource "azurerm_role_assignment" "document_intelligence_user" {
  for_each = var.document_intelligence_user_principal_ids

  name = uuidv5(local.role_assignment_uuid_namespace, lower(join("|", [
    azurerm_cognitive_account.document_intelligence.id,
    local.cognitive_user_role_definition,
    each.value,
    "ServicePrincipal",
    "true",
  ])))

  scope                            = azurerm_cognitive_account.document_intelligence.id
  role_definition_name             = local.cognitive_user_role_definition
  principal_id                     = each.value
  principal_type                   = "ServicePrincipal"
  skip_service_principal_aad_check = true
}

resource "azurerm_role_assignment" "foundry_user" {
  for_each = var.foundry_enabled ? var.foundry_user_principal_ids : {}

  name = uuidv5(local.role_assignment_uuid_namespace, lower(join("|", [
    azurerm_cognitive_account.foundry[0].id,
    local.cognitive_user_role_definition,
    each.value,
    "ServicePrincipal",
    "true",
  ])))

  scope                            = azurerm_cognitive_account.foundry[0].id
  role_definition_name             = local.cognitive_user_role_definition
  principal_id                     = each.value
  principal_type                   = "ServicePrincipal"
  skip_service_principal_aad_check = true
}

resource "azurerm_role_assignment" "foundry_openai_user" {
  for_each = var.foundry_enabled ? var.foundry_openai_user_principal_ids : {}

  name = uuidv5(local.role_assignment_uuid_namespace, lower(join("|", [
    azurerm_cognitive_account.foundry[0].id,
    local.cognitive_openai_user_role_definition,
    each.value,
    "ServicePrincipal",
    "true",
  ])))

  scope                            = azurerm_cognitive_account.foundry[0].id
  role_definition_name             = local.cognitive_openai_user_role_definition
  principal_id                     = each.value
  principal_type                   = "ServicePrincipal"
  skip_service_principal_aad_check = true
}
