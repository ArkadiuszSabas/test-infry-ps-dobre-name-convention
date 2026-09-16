subscription_id                 = "ade38c32-9ade-4049-a9e1-bce6d1692438"
environment                     = "test"
application_resource_group_name = "rg-ocr-test"
key_vault_name                  = "ee7c45-kv-ocr-test-01"
key_vault_resource_group_name   = "rg-ocr-test"

cmk_identities = {
  cmk-document-intelligence = { name = "id-ocr-test-cmk-document-intelligence-01" }
  cmk-postgresql            = { name = "id-ocr-test-cmk-postgresql-01" }
  cmk-storage               = { name = "id-ocr-test-cmk-storage-01" }
}
