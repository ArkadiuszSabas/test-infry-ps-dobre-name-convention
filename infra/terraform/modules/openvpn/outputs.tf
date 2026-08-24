output "virtual_machine_id" {
  description = "OpenVPN virtual machine resource ID."
  value       = azurerm_linux_virtual_machine.this.id
}

output "virtual_machine_name" {
  description = "OpenVPN virtual machine name."
  value       = azurerm_linux_virtual_machine.this.name
}

output "private_ip_address" {
  description = "OpenVPN server private IP address."
  value       = azurerm_network_interface.this.private_ip_address
}

output "public_ip_address" {
  description = "OpenVPN server public IP address."
  value       = azurerm_public_ip.this.ip_address
}

output "public_fqdn" {
  description = "OpenVPN server public FQDN when a DNS label is configured."
  value       = azurerm_public_ip.this.fqdn
}

output "endpoint" {
  description = "OpenVPN UDP endpoint."
  value       = "udp://${coalesce(azurerm_public_ip.this.fqdn, azurerm_public_ip.this.ip_address)}:${var.openvpn_port}"
}

output "key_vault_secret_names" {
  description = "Key Vault secret names consumed by the OpenVPN VM."
  value       = var.key_vault_secret_names
}
