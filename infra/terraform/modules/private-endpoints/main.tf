resource "azurerm_private_endpoint" "this" {
  for_each = var.private_endpoints

  name                = each.value.name
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = each.value.subnet_id
  tags                = var.tags

  private_service_connection {
    name                           = "psc-${each.value.name}"
    private_connection_resource_id = each.value.private_connection_resource_id
    is_manual_connection           = false
    subresource_names              = each.value.subresource_names
  }

  dynamic "private_dns_zone_group" {
    for_each = length(each.value.private_dns_zone_ids) == 0 ? [] : [each.value.private_dns_zone_ids]

    content {
      name                 = "default"
      private_dns_zone_ids = private_dns_zone_group.value
    }
  }
}
