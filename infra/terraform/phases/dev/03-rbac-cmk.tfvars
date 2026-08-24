subscription_id                 = "fe31d3c8-576f-4c09-913c-635306834ff0"
environment                     = "dev"
application_resource_group_name = "rg-ocr-dev"
key_vault_name                  = "kv-ocr-dev-cmk-arksab2"
key_vault_resource_group_name   = "rg-ocr-dev"

cmk_identities = {
  cmk-document-intelligence = { name = "id-ocr-dev-cmk-document-intelligence-01" }
  cmk-postgresql            = { name = "id-ocr-dev-cmk-postgresql-01" }
  cmk-storage               = { name = "id-ocr-dev-cmk-storage-01" }
}
