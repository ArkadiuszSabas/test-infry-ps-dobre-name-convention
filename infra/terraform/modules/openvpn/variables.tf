variable "virtual_machine_name" {
  description = "OpenVPN virtual machine name."
  type        = string
}

variable "virtual_machine_size" {
  description = "OpenVPN virtual machine size."
  type        = string
  default     = "Standard_B2ts_v2"
}

variable "location" {
  description = "Azure region for OpenVPN resources."
  type        = string
}

variable "resource_group_name" {
  description = "Resource group where OpenVPN resources are created."
  type        = string
}

variable "subnet_id" {
  description = "Subnet ID for the OpenVPN VM NIC."
  type        = string
}

variable "identity_id" {
  description = "User-assigned managed identity resource ID attached to the OpenVPN VM."
  type        = string
}

variable "identity_client_id" {
  description = "Client ID of the OpenVPN VM user-assigned managed identity used for Key Vault access."
  type        = string
}

variable "key_vault_name" {
  description = "Dedicated OpenVPN runtime Key Vault name that stores server PKI material except the CA private key."
  type        = string
}

variable "ca_key_vault_name" {
  description = "Dedicated OpenVPN operator-only Key Vault name that stores the CA private key."
  type        = string
}

variable "ca_key_secret_name" {
  description = "Operator-only Key Vault secret name used for the OpenVPN CA private key."
  type        = string

  validation {
    condition     = can(regex("^[0-9A-Za-z-]{1,127}$", var.ca_key_secret_name))
    error_message = "OpenVPN CA key secret name must be 1-127 characters and contain only letters, digits, or hyphens."
  }
}

variable "key_vault_secret_names" {
  description = "Key Vault secret names used by the OpenVPN VM certificate sync job."
  type = object({
    ca_cert         = string
    server_cert     = string
    server_key      = string
    dh_pem          = string
    tls_crypt_key   = string
    clients_json    = string
    rotation_bundle = string
    rotation_state  = string
  })

  validation {
    condition = alltrue([
      for secret_name in values(var.key_vault_secret_names) :
      can(regex("^[0-9A-Za-z-]{1,127}$", secret_name))
    ])
    error_message = "OpenVPN Key Vault secret names must be 1-127 characters and contain only letters, digits, or hyphens."
  }
}

variable "private_access_cidrs" {
  description = "CIDR blocks reachable by OpenVPN clients with the private access profile."
  type        = list(string)

  validation {
    condition = alltrue([
      for cidr in var.private_access_cidrs : can(cidrnetmask(cidr))
    ])
    error_message = "OpenVPN private access CIDRs must be valid CIDR blocks."
  }
}

variable "certificate_sync_interval_minutes" {
  description = "Cron interval, in minutes, for refreshing OpenVPN certificates and active clients from Key Vault."
  type        = number
  default     = 30

  validation {
    condition     = var.certificate_sync_interval_minutes >= 5 && var.certificate_sync_interval_minutes <= 59
    error_message = "OpenVPN certificate sync interval must be between 5 and 59 minutes."
  }
}

variable "public_ip_name" {
  description = "Public IP resource name for the OpenVPN server."
  type        = string
}

variable "public_dns_label" {
  description = "Optional DNS label for the OpenVPN server Public IP."
  type        = string
  default     = null
  nullable    = true

  validation {
    condition     = var.public_dns_label == null ? true : can(regex("^[a-z][a-z0-9-]{1,61}[a-z0-9]$", var.public_dns_label))
    error_message = "OpenVPN public DNS label must be 3-63 lowercase letters, digits, or hyphens, start with a letter, and end with a letter or digit."
  }
}

variable "network_security_group_name" {
  description = "Network Security Group name for the OpenVPN VM NIC."
  type        = string
}

variable "network_interface_name" {
  description = "Network interface name for the OpenVPN VM."
  type        = string
}

variable "admin_username" {
  description = "Linux administrator username for the OpenVPN VM."
  type        = string
  default     = "azureuser"
}

variable "admin_ssh_public_key" {
  description = "SSH public key authorized for the OpenVPN VM administrator."
  type        = string
  sensitive   = false
}

variable "ssh_port" {
  description = "High TCP port used by administrative SSH."
  type        = number
  default     = 49222

  validation {
    condition     = var.ssh_port >= 1024 && var.ssh_port <= 65535
    error_message = "OpenVPN SSH port must be between 1024 and 65535."
  }
}

variable "ssh_source_address_prefixes" {
  description = "Trusted CIDR ranges allowed to SSH to the OpenVPN VM. Leave empty to disable SSH ingress."
  type        = set(string)
  default     = []

  validation {
    condition = alltrue([
      for prefix in var.ssh_source_address_prefixes : can(cidrnetmask(prefix)) && prefix != "0.0.0.0/0"
    ])
    error_message = "OpenVPN SSH source prefixes must be valid CIDR blocks and must not include 0.0.0.0/0."
  }
}

variable "ssh_operator_public_keys" {
  description = "Named operator SSH public keys authorized by the SSH hardening extension. The VM bootstrap admin key is not kept in this direct-operator key set."
  type        = map(string)
  default     = {}

  validation {
    condition = alltrue([
      for name, key in var.ssh_operator_public_keys :
      can(regex("^[A-Za-z][A-Za-z0-9_-]{0,31}$", name)) && can(regex("^ssh-ed25519\\s+[A-Za-z0-9+/=]+(?:\\s+[^\\r\\n]+)?$", key))
    ])
    error_message = "OpenVPN SSH operator public keys must use token-like names and ssh-ed25519 public key values."
  }
}

variable "openvpn_port" {
  description = "OpenVPN UDP listener port."
  type        = number
  default     = 1194

  validation {
    condition     = var.openvpn_port >= 1 && var.openvpn_port <= 65535
    error_message = "OpenVPN port must be between 1 and 65535."
  }
}

variable "client_cidr" {
  description = "CIDR block assigned to OpenVPN clients."
  type        = string

  validation {
    condition     = can(cidrnetmask(var.client_cidr)) && can(regex("/24$", var.client_cidr))
    error_message = "OpenVPN client CIDR must be a valid /24 CIDR block."
  }
}

variable "os_disk_size_gb" {
  description = "OpenVPN VM OS disk size in GB."
  type        = number
  default     = 32
}

variable "tags" {
  description = "Common tags applied to OpenVPN resources."
  type        = map(string)
}

variable "profile_lock_storage_account_name" {
  description = "Storage Account used by profile lifecycle tooling for the shared operation lock."
  type        = string
}

variable "profile_lock_container_name" {
  description = "Blob container used by profile lifecycle tooling for the shared operation lock."
  type        = string
}
