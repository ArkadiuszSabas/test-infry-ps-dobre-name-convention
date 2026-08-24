variable "namespace_name" {
  description = "Service Bus namespace name."
  type        = string
}

variable "location" {
  description = "Azure region for Service Bus resources."
  type        = string
}

variable "resource_group_name" {
  description = "Resource group where Service Bus resources are created."
  type        = string
}

variable "sku" {
  description = "Service Bus namespace SKU."
  type        = string

  validation {
    condition     = var.sku == "Standard"
    error_message = "Service Bus namespace SKU must be Standard. Premium and Private Endpoint are outside this slice."
  }
}

variable "public_network_access_enabled" {
  description = "Whether public network access is enabled for the Service Bus namespace."
  type        = bool
  default     = true
}

variable "network_rule_default_action" {
  description = "Default Service Bus network rule action."
  type        = string
  default     = "Deny"

  validation {
    condition     = contains(["Allow", "Deny"], var.network_rule_default_action)
    error_message = "Service Bus network rule default action must be Allow or Deny."
  }
}

variable "network_rule_ip_rules" {
  description = "IPv4 addresses or CIDR blocks allowed to reach the Service Bus namespace public endpoint."
  type        = set(string)
  default     = []

  validation {
    condition = alltrue([
      for ip_rule in var.network_rule_ip_rules :
      can(cidrnetmask(ip_rule)) || can(cidrnetmask("${ip_rule}/32"))
    ])
    error_message = "Service Bus network rule IP rules must be valid IPv4 addresses or CIDR blocks."
  }
}

variable "queues" {
  description = "Service Bus queues keyed by queue name."
  type = map(object({
    dead_lettering_on_message_expiration = bool
    default_message_ttl                  = string
    lock_duration                        = string
    max_delivery_count                   = number
    max_size_in_megabytes                = number
    partitioning_enabled                 = bool
  }))
}

variable "queue_sender_principal_ids" {
  description = "Principal IDs granted Azure Service Bus Data Sender per queue."
  type        = map(map(string))
}

variable "queue_receiver_principal_ids" {
  description = "Principal IDs granted Azure Service Bus Data Receiver per queue."
  type        = map(map(string))
}

variable "tags" {
  description = "Common tags applied to Service Bus resources."
  type        = map(string)
}
