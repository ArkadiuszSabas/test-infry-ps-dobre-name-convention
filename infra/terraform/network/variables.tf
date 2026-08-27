variable "subscription_id" {
  description = "Target environment subscription ID."
  type        = string

  validation {
    condition     = can(regex("^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$", var.subscription_id))
    error_message = "subscription_id must be an Azure subscription GUID."
  }
}

variable "location" {
  description = "Azure region."
  type        = string
  default     = "swedencentral"
}

variable "environment" {
  description = "Deployment environment identifier used in resource names."
  type        = string
}

variable "region_code" {
  description = "Short Azure region identifier used by the naming convention."
  type        = string
}

variable "organization_token" {
  description = "Organization identifier used by the naming convention."
  type        = string
}

variable "tenant_prefix" {
  description = "Tenant prefix used by the naming convention."
  type        = string
}

variable "app_id" {
  description = "Application identifier used by the naming convention."
  type        = string
}

variable "instance_number" {
  description = "Application instance identifier used by the naming convention."
  type        = string
}

variable "network_resource_group_name" {
  description = "Existing ProService resource group containing the VNet and network-owned resources."
  type        = string
}

variable "private_dns_resource_group_name" {
  description = "Existing resource group containing the Private DNS Zones."
  type        = string
}

variable "private_dns_subscription_id" {
  description = "Hub subscription ID containing the shared Private DNS Zones."
  type        = string

  validation {
    condition     = can(regex("^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$", var.private_dns_subscription_id))
    error_message = "private_dns_subscription_id must be an Azure subscription GUID."
  }
}

variable "application_resource_group_name" {
  description = "Existing ProService resource group containing Private Endpoint target resources."
  type        = string
}

variable "network_design_approved" {
  description = "Explicit confirmation that the existing topology and migration procedure were approved by ProService Networking."
  type        = bool
  default     = false
}

variable "virtual_network_name" {
  description = "Existing ProService virtual network name."
  type        = string
}

variable "expected_network_address_space" {
  description = "Approved address spaces expected on the existing VNet."
  type        = set(string)
}

variable "private_endpoint_subnet_name" {
  description = "Existing Private Endpoint subnet name."
  type        = string
}

variable "expected_private_endpoint_subnet_cidr" {
  description = "Approved CIDR expected on the existing Private Endpoint subnet."
  type        = string

  validation {
    condition     = can(cidrnetmask(var.expected_private_endpoint_subnet_cidr)) && can(regex("/24$", var.expected_private_endpoint_subnet_cidr))
    error_message = "The expected Private Endpoint subnet CIDR must be a valid /24 block."
  }
}

variable "container_apps_infrastructure_subnet_name" {
  description = "Existing subnet delegated to Azure Container Apps environments."
  type        = string
}

variable "expected_container_apps_infrastructure_subnet_cidr" {
  description = "Approved CIDR expected on the existing Container Apps infrastructure subnet."
  type        = string

  validation {
    condition     = can(cidrnetmask(var.expected_container_apps_infrastructure_subnet_cidr)) && try(tonumber(split("/", var.expected_container_apps_infrastructure_subnet_cidr)[1]) <= 27, false)
    error_message = "The expected Container Apps subnet CIDR must be a valid /27 or larger block."
  }
}

variable "additional_container_apps_private_dns_locations" {
  description = "Additional Container Apps regions requiring Private DNS zones."
  type        = set(string)
  default     = []

  validation {
    condition     = alltrue([for location in var.additional_container_apps_private_dns_locations : can(regex("^[a-z0-9]+$", location))])
    error_message = "Additional Container Apps Private DNS locations must use Azure canonical location names."
  }
}

variable "private_endpoints" {
  description = "Complete Private Endpoint desired state keyed by logical service name. Keep the map cumulative after endpoints are introduced."
  type = map(object({
    private_connection_resource_id = string
    subresource_names              = list(string)
    private_dns_zone_ids           = list(string)
  }))
  default = {}
}

variable "container_apps_environment_private_dns" {
  description = "Apex and wildcard records for the Container Apps Environment Private Endpoint."
  type = object({
    private_endpoint_key = string
    default_domain       = string
    private_dns_zone_key = optional(string, "container_apps")
  })
  default  = null
  nullable = true

  validation {
    condition = var.container_apps_environment_private_dns == null ? true : (
      length(split(".", var.container_apps_environment_private_dns.default_domain)) >= 3
    )
    error_message = "Container Apps Environment default_domain must be a fully qualified domain name."
  }
}

variable "tags" {
  description = "Common tags applied to network-owned resources."
  type        = map(string)
}
