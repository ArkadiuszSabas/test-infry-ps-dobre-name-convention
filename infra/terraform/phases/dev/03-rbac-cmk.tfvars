subscription_id                 = "fe31d3c8-576f-4c09-913c-635306834ff0"
environment                     = "dev"
application_resource_group_name = "rg-ocr-dev"
key_vault_name                  = "kv-ocr-dev-cmk-arksab2"
key_vault_resource_group_name   = "rg-ocr-dev"

cmk_identities = {
  cmk-document-intelligence = { name = "id-dev-cmk-document-intelligence" }
  cmk-foundry               = { name = "id-dev-cmk-foundry" }
  cmk-postgresql            = { name = "id-dev-cmk-postgresql" }
  cmk-servicebus            = { name = "id-dev-cmk-servicebus" }
  cmk-storage               = { name = "id-dev-cmk-storage" }
}
