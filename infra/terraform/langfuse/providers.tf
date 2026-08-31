provider "azurerm" {
  subscription_id                 = var.subscription_id
  resource_provider_registrations = "none"
  storage_use_azuread             = true

  features {
    storage {
      data_plane_available = false
    }
  }
}

provider "azurerm" {
  alias                           = "hub"
  subscription_id                 = var.private_dns_subscription_id
  resource_provider_registrations = "none"

  features {}
}

provider "azapi" {
  disable_default_output = true
}
