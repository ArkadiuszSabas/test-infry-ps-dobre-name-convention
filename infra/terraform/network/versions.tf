terraform {
  required_version = "~> 1.15.0"

  backend "azurerm" {}

  required_providers {
    azapi = {
      source  = "azure/azapi"
      version = "2.9.0"
    }
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "4.69.0"
    }
  }
}
