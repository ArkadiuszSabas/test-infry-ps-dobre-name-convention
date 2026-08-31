terraform {
  required_version = "~> 1.15.0"

  backend "azurerm" {}

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.69.0"
    }
    azapi = {
      source  = "Azure/azapi"
      version = "~> 2.9.0"
    }
    time = {
      source  = "hashicorp/time"
      version = "~> 0.13.0"
    }
  }
}
