output "id" {
  description = "Service Bus namespace resource ID."
  value       = azurerm_servicebus_namespace.this.id
}

output "name" {
  description = "Service Bus namespace name."
  value       = azurerm_servicebus_namespace.this.name
}

output "endpoint" {
  description = "Service Bus namespace endpoint."
  value       = azurerm_servicebus_namespace.this.endpoint
}

output "fully_qualified_namespace" {
  description = "Service Bus fully qualified namespace."
  value       = "${azurerm_servicebus_namespace.this.name}.servicebus.windows.net"
}

output "queue_ids" {
  description = "Service Bus queue resource IDs keyed by queue name."
  value       = { for queue_name, queue in azurerm_servicebus_queue.this : queue_name => queue.id }
}

output "queue_names" {
  description = "Service Bus queue names."
  value       = keys(azurerm_servicebus_queue.this)
}
