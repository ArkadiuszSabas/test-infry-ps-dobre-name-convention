locals {
  role_assignment_uuid_namespace = "6ba7b811-9dad-11d1-80b4-00c04fd430c8"
  sender_role_definition         = "Azure Service Bus Data Sender"
  receiver_role_definition       = "Azure Service Bus Data Receiver"

  receiver_role_assignments = {
    for assignment in flatten([
      for queue_name, principal_ids in var.queue_receiver_principal_ids : [
        for principal_name, principal_id in principal_ids : {
          key          = "${queue_name}.${principal_name}"
          queue_name   = queue_name
          principal_id = principal_id
        }
      ]
    ]) : assignment.key => assignment
  }

  sender_role_assignments = {
    for assignment in flatten([
      for queue_name, principal_ids in var.queue_sender_principal_ids : [
        for principal_name, principal_id in principal_ids : {
          key          = "${queue_name}.${principal_name}"
          queue_name   = queue_name
          principal_id = principal_id
        }
      ]
    ]) : assignment.key => assignment
  }
}

resource "azurerm_servicebus_namespace" "this" {
  name                = var.namespace_name
  location            = var.location
  resource_group_name = var.resource_group_name
  sku                 = var.sku

  local_auth_enabled            = false
  minimum_tls_version           = "1.2"
  public_network_access_enabled = var.public_network_access_enabled

  network_rule_set {
    default_action                = var.network_rule_default_action
    public_network_access_enabled = var.public_network_access_enabled
    trusted_services_allowed      = false
    ip_rules                      = sort(tolist(var.network_rule_ip_rules))
  }

  lifecycle {
    precondition {
      condition     = !(var.public_network_access_enabled && var.network_rule_default_action == "Deny" && length(var.network_rule_ip_rules) == 0)
      error_message = "Service Bus public network access with default Deny requires at least one network_rule_ip_rules entry."
    }
  }

  tags = var.tags
}

resource "azurerm_servicebus_queue" "this" {
  for_each = var.queues

  name         = each.key
  namespace_id = azurerm_servicebus_namespace.this.id

  dead_lettering_on_message_expiration = each.value.dead_lettering_on_message_expiration
  default_message_ttl                  = each.value.default_message_ttl
  lock_duration                        = each.value.lock_duration
  max_delivery_count                   = each.value.max_delivery_count
  max_size_in_megabytes                = each.value.max_size_in_megabytes
  partitioning_enabled                 = each.value.partitioning_enabled
}

resource "azurerm_role_assignment" "sender" {
  for_each = local.sender_role_assignments

  name = uuidv5(local.role_assignment_uuid_namespace, lower(join("|", [
    azurerm_servicebus_queue.this[each.value.queue_name].id,
    local.sender_role_definition,
    each.value.principal_id,
    "ServicePrincipal",
    "true",
  ])))

  scope                            = azurerm_servicebus_queue.this[each.value.queue_name].id
  role_definition_name             = local.sender_role_definition
  principal_id                     = each.value.principal_id
  principal_type                   = "ServicePrincipal"
  skip_service_principal_aad_check = true
}

resource "azurerm_role_assignment" "receiver" {
  for_each = local.receiver_role_assignments

  name = uuidv5(local.role_assignment_uuid_namespace, lower(join("|", [
    azurerm_servicebus_queue.this[each.value.queue_name].id,
    local.receiver_role_definition,
    each.value.principal_id,
    "ServicePrincipal",
    "true",
  ])))

  scope                            = azurerm_servicebus_queue.this[each.value.queue_name].id
  role_definition_name             = local.receiver_role_definition
  principal_id                     = each.value.principal_id
  principal_type                   = "ServicePrincipal"
  skip_service_principal_aad_check = true
}
