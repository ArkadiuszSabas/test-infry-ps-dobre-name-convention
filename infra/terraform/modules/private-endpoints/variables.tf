variable "location" {
  description = "Azure region for Private Endpoints."
  type        = string
}

variable "resource_group_name" {
  description = "Resource group where Private Endpoints are created."
  type        = string
}

variable "private_endpoints" {
  description = "Private Endpoint definitions keyed by logical endpoint name."
  type = map(object({
    name                           = string
    subnet_id                      = string
    private_connection_resource_id = string
    subresource_names              = list(string)
    private_dns_zone_ids           = list(string)
  }))
}

variable "tags" {
  description = "Common tags applied to Private Endpoints."
  type        = map(string)
}
