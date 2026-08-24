variable "name" {
  description = "Container Registry name."
  type        = string
}

variable "location" {
  description = "Azure region for Container Registry."
  type        = string
}

variable "resource_group_name" {
  description = "Resource group where Container Registry is created."
  type        = string
}

variable "sku" {
  description = "Container Registry SKU."
  type        = string
}

variable "pull_principal_ids" {
  description = "Principal IDs granted AcrPull."
  type        = map(string)
}

variable "push_principal_ids" {
  description = "Principal IDs granted AcrPush."
  type        = map(string)
  default     = {}
}

variable "tags" {
  description = "Common tags applied to Container Registry."
  type        = map(string)
}
