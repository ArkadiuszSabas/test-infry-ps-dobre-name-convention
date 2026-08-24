resource "azurerm_resource_group" "environment" {
  name     = var.environment_resource_group_name
  location = var.location

  tags = merge(var.tags, {
    scope = "environment"
  })
}
