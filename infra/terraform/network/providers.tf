provider "azurerm" {
  subscription_id                 = var.subscription_id
  resource_provider_registrations = "none"

  features {}
}

provider "azapi" {
  disable_default_output = true
}
