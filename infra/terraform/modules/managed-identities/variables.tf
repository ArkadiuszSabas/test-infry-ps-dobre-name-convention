variable "location" {
  description = "Azure region for managed identities."
  type        = string
}

variable "resource_group_name" {
  description = "Resource group where managed identities are created."
  type        = string
}

variable "identities" {
  description = "Managed identity definitions keyed by workload name."
  type = map(object({
    name = string
  }))
}

variable "tags" {
  description = "Common tags applied to managed identities."
  type        = map(string)
}
