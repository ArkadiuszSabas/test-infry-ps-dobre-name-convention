variable "virtual_network_name" {
  description = "Virtual network name for the environment."
  type        = string
}

variable "location" {
  description = "Azure region for networking resources."
  type        = string
}

variable "resource_group_name" {
  description = "Resource group where networking resources are created."
  type        = string
}

variable "shared_private_dns_resource_group_name" {
  description = "Optional existing resource group that owns shared Private DNS zones. Null creates environment-local zones."
  type        = string
  default     = null
  nullable    = true
}

variable "additional_container_apps_private_dns_locations" {
  description = "Additional Azure locations whose regional Container Apps Private DNS zones are created with locally owned zones."
  type        = set(string)
  default     = []

  validation {
    condition     = alltrue([for location in var.additional_container_apps_private_dns_locations : can(regex("^[a-z0-9]+$", location))])
    error_message = "Additional Container Apps Private DNS locations must use Azure canonical location names with lowercase letters and digits."
  }
}

variable "address_space" {
  description = "Address space assigned to the environment virtual network."
  type        = list(string)

  validation {
    condition = alltrue([
      for cidr in var.address_space : can(cidrnetmask(cidr))
    ])
    error_message = "Networking address_space entries must be valid CIDR blocks."
  }
}

variable "private_endpoint_subnet_name" {
  description = "Subnet name for application service Private Endpoints."
  type        = string
}

variable "private_endpoint_subnet_cidr" {
  description = "CIDR block for application service Private Endpoints."
  type        = string

  validation {
    condition     = can(cidrnetmask(var.private_endpoint_subnet_cidr)) && can(regex("/24$", var.private_endpoint_subnet_cidr))
    error_message = "Application Private Endpoint subnet CIDR must be a valid /24 CIDR block."
  }
}

variable "container_apps_infrastructure_subnet_name" {
  description = "Subnet name delegated to Azure Container Apps environments."
  type        = string
}

variable "container_apps_infrastructure_subnet_cidr" {
  description = "CIDR block delegated to Azure Container Apps environments."
  type        = string

  validation {
    condition     = can(cidrnetmask(var.container_apps_infrastructure_subnet_cidr)) && try(tonumber(split("/", var.container_apps_infrastructure_subnet_cidr)[1]) <= 27, false)
    error_message = "Container Apps infrastructure subnet CIDR must be a valid CIDR block with a /27 or larger address range."
  }
}

variable "openvpn_server_subnet_name" {
  description = "Subnet name for the optional OpenVPN server VM."
  type        = string
}

variable "openvpn_server_subnet_cidr" {
  description = "CIDR block for the optional OpenVPN server VM subnet."
  type        = string

  validation {
    condition     = can(cidrnetmask(var.openvpn_server_subnet_cidr)) && try(tonumber(split("/", var.openvpn_server_subnet_cidr)[1]) <= 27, false)
    error_message = "OpenVPN server subnet CIDR must be a valid CIDR block with a /27 or larger address range."
  }
}

variable "tags" {
  description = "Common tags applied to networking resources."
  type        = map(string)
}
