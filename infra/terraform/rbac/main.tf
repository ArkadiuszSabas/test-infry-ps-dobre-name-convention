locals {
  role_assignment_uuid_namespace = "6ba7b811-9dad-11d1-80b4-00c04fd430c8"
}

data "azurerm_user_assigned_identity" "workload" {
  for_each = var.workload_identities

  name                = each.value.name
  resource_group_name = var.application_resource_group_name
}

locals {
  role_assignment_principal_ids = {
    for key, assignment in var.role_assignments :
    key => try(data.azurerm_user_assigned_identity.workload[assignment.workload_identity_key].principal_id, assignment.principal_id)
  }
}

resource "azurerm_role_assignment" "this" {
  for_each = var.role_assignments

  name = uuidv5(local.role_assignment_uuid_namespace, lower(join("|", [
    each.value.scope,
    each.value.role_definition_name,
    local.role_assignment_principal_ids[each.key],
  ])))

  scope                            = each.value.scope
  role_definition_name             = each.value.role_definition_name
  principal_id                     = local.role_assignment_principal_ids[each.key]
  principal_type                   = each.value.principal_type
  skip_service_principal_aad_check = each.value.skip_service_principal_aad_check

  lifecycle {
    precondition {
      condition     = each.value.workload_identity_key == null || contains(keys(var.workload_identities), each.value.workload_identity_key)
      error_message = "workload_identity_key must exist in workload_identities."
    }

    precondition {
      condition = startswith(
        lower(each.value.scope),
        "/subscriptions/${lower(var.subscription_id)}/",
      )
      error_message = "RBAC assignment scope must belong to the target subscription."
    }
  }
}
