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

provider "azapi" {
  disable_default_output = true
}
