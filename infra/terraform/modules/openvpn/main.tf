locals {
  authorized_ssh_public_keys = distinct(compact([
    for operator_name in sort(keys(var.ssh_operator_public_keys)) : var.ssh_operator_public_keys[operator_name]
  ]))

  server_config = {
    access_profiles                   = { private = var.private_access_cidrs }
    certificate_sync_interval_minutes = var.certificate_sync_interval_minutes
    client_cidr                       = var.client_cidr
    identity_client_id                = var.identity_client_id
    key_vault_name                    = var.key_vault_name
    key_vault_secret_names            = var.key_vault_secret_names
    ca_key_vault_name                 = var.ca_key_vault_name
    ca_key_secret_name                = var.ca_key_secret_name
    private_dns_ip                    = "168.63.129.16"
    protocol                          = "udp"
    remote_host                       = azurerm_public_ip.this.ip_address
    port                              = var.openvpn_port
  }
}

resource "azurerm_public_ip" "this" {
  name                = var.public_ip_name
  location            = var.location
  resource_group_name = var.resource_group_name
  allocation_method   = "Static"
  sku                 = "Standard"
  domain_name_label   = var.public_dns_label

  tags = var.tags
}

resource "azurerm_network_security_group" "this" {
  name                = var.network_security_group_name
  location            = var.location
  resource_group_name = var.resource_group_name

  tags = var.tags
}

resource "azurerm_network_security_rule" "openvpn" {
  name                        = "Allow-OpenVPN-UDP"
  priority                    = 100
  direction                   = "Inbound"
  access                      = "Allow"
  protocol                    = "Udp"
  source_port_range           = "*"
  destination_port_range      = tostring(var.openvpn_port)
  source_address_prefix       = "Internet"
  destination_address_prefix  = "*"
  resource_group_name         = var.resource_group_name
  network_security_group_name = azurerm_network_security_group.this.name
}

resource "azurerm_network_security_rule" "ssh" {
  count = length(var.ssh_source_address_prefixes) == 0 ? 0 : 1

  name                        = "Allow-SSH-Admin"
  priority                    = 110
  direction                   = "Inbound"
  access                      = "Allow"
  protocol                    = "Tcp"
  source_port_range           = "*"
  destination_port_range      = tostring(var.ssh_port)
  source_address_prefixes     = sort(tolist(var.ssh_source_address_prefixes))
  destination_address_prefix  = "*"
  resource_group_name         = var.resource_group_name
  network_security_group_name = azurerm_network_security_group.this.name
}

resource "azurerm_network_security_rule" "deny_virtual_network_inbound" {
  name                        = "Deny-VNet-Inbound"
  priority                    = 4096
  direction                   = "Inbound"
  access                      = "Deny"
  protocol                    = "*"
  source_port_range           = "*"
  destination_port_range      = "*"
  source_address_prefix       = "VirtualNetwork"
  destination_address_prefix  = "*"
  resource_group_name         = var.resource_group_name
  network_security_group_name = azurerm_network_security_group.this.name
}

resource "azurerm_network_interface" "this" {
  name                           = var.network_interface_name
  location                       = var.location
  resource_group_name            = var.resource_group_name
  ip_forwarding_enabled          = true
  accelerated_networking_enabled = false

  ip_configuration {
    name                          = "primary"
    subnet_id                     = var.subnet_id
    private_ip_address_allocation = "Dynamic"
    public_ip_address_id          = azurerm_public_ip.this.id
  }

  tags = var.tags
}

resource "azurerm_virtual_machine_extension" "ssh_admin" {
  name                       = "docmind-openvpn-ssh-admin"
  virtual_machine_id         = azurerm_linux_virtual_machine.this.id
  publisher                  = "Microsoft.Azure.Extensions"
  type                       = "CustomScript"
  type_handler_version       = "2.1"
  auto_upgrade_minor_version = true

  settings = jsonencode({
    script = base64gzip(templatefile("${path.module}/ssh-admin-extension.sh.tftpl", {
      admin_username                    = var.admin_username
      authorized_keys_base64            = base64encode("${join("\n", local.authorized_ssh_public_keys)}\n")
      openvpn_profile_script_base64     = base64encode(file("${path.module}/../../../openvpn-profiles.ps1"))
      profile_lock_container_name       = var.profile_lock_container_name
      profile_lock_storage_account_name = var.profile_lock_storage_account_name
      server_json_base64                = base64encode(jsonencode(local.server_config))
      ssh_enabled                       = length(var.ssh_source_address_prefixes) == 0 ? "false" : "true"
      ssh_port                          = var.ssh_port
    }))
  })

  tags = var.tags
}

resource "azurerm_network_interface_security_group_association" "this" {
  network_interface_id      = azurerm_network_interface.this.id
  network_security_group_id = azurerm_network_security_group.this.id
}

resource "azurerm_linux_virtual_machine" "this" {
  name                            = var.virtual_machine_name
  location                        = var.location
  resource_group_name             = var.resource_group_name
  size                            = var.virtual_machine_size
  admin_username                  = var.admin_username
  disable_password_authentication = true
  network_interface_ids           = [azurerm_network_interface.this.id]
  custom_data = base64encode(templatefile("${path.module}/cloud-init.yaml.tftpl", {
    clients_json = jsonencode({})
    server_json  = jsonencode(local.server_config)
  }))

  admin_ssh_key {
    username   = var.admin_username
    public_key = var.admin_ssh_public_key
  }

  identity {
    type         = "UserAssigned"
    identity_ids = [var.identity_id]
  }

  os_disk {
    caching              = "ReadWrite"
    storage_account_type = "StandardSSD_LRS"
    disk_size_gb         = var.os_disk_size_gb
  }

  source_image_reference {
    publisher = "Canonical"
    offer     = "0001-com-ubuntu-server-jammy"
    sku       = "22_04-lts-gen2"
    version   = "latest"
  }

  tags = var.tags

  lifecycle {
    ignore_changes = [custom_data]
  }
}
