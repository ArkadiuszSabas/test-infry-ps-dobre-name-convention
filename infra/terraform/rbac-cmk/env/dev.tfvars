subscription_id                 = "16060ea2-28be-4b09-8e6d-060249d69ddd"
environment                     = "dev"
application_resource_group_name = "rg-ocr-dev-arksab"
key_vault_name                  = "kv-ocr-dev-cmk-arksab"
key_vault_resource_group_name   = "rg-ocr-dev-arksab"

cmk_identities = {
  cmk-document-intelligence = { name = "id-dev-cmk-document-intelligence" }
  cmk-foundry               = { name = "id-dev-cmk-foundry" }
  cmk-postgresql            = { name = "id-dev-cmk-postgresql" }
  cmk-servicebus            = { name = "id-dev-cmk-servicebus" }
  cmk-storage               = { name = "id-dev-cmk-storage" }
}
