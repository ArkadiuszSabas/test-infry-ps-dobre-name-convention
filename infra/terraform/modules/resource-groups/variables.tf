variable "location" {
  description = "Azure region for resource groups."
  type        = string
}

variable "environment_resource_group_name" {
  description = "Resource group dedicated to the selected environment."
  type        = string
}

variable "tags" {
  description = "Common tags applied to resource groups."
  type        = map(string)
}
