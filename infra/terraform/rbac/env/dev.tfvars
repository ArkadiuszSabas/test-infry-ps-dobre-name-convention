subscription_id = "fe31d3c8-576f-4c09-913c-635306834ff0"
app_id          = "ocr"
environment     = "dev"
instance_number = "01"

application_resource_group_name = "rg-ocr-dev"

workload_identity_workloads = [
  "web",
  "api",
  "api-migrator",
  "dapr-servicebus-api",
  "dapr-servicebus-worker",
  "llmmagic",
  "worker",
]

role_assignments = {
  acr-pull-web = {
    scope                            = "/subscriptions/fe31d3c8-576f-4c09-913c-635306834ff0/resourceGroups/rg-ocr-dev/providers/Microsoft.ContainerRegistry/registries/ee7c45crocrdev01"
    role_definition_name             = "AcrPull"
    workload_identity_key            = "web"
    principal_type                   = "ServicePrincipal"
    skip_service_principal_aad_check = true
  }
  acr-pull-api = {
    scope                            = "/subscriptions/fe31d3c8-576f-4c09-913c-635306834ff0/resourceGroups/rg-ocr-dev/providers/Microsoft.ContainerRegistry/registries/ee7c45crocrdev01"
    role_definition_name             = "AcrPull"
    workload_identity_key            = "api"
    principal_type                   = "ServicePrincipal"
    skip_service_principal_aad_check = true
  }
  acr-pull-api-migrator = {
    scope                            = "/subscriptions/fe31d3c8-576f-4c09-913c-635306834ff0/resourceGroups/rg-ocr-dev/providers/Microsoft.ContainerRegistry/registries/ee7c45crocrdev01"
    role_definition_name             = "AcrPull"
    workload_identity_key            = "api-migrator"
    principal_type                   = "ServicePrincipal"
    skip_service_principal_aad_check = true
  }
  acr-pull-llmmagic = {
    scope                            = "/subscriptions/fe31d3c8-576f-4c09-913c-635306834ff0/resourceGroups/rg-ocr-dev/providers/Microsoft.ContainerRegistry/registries/ee7c45crocrdev01"
    role_definition_name             = "AcrPull"
    workload_identity_key            = "llmmagic"
    principal_type                   = "ServicePrincipal"
    skip_service_principal_aad_check = true
  }
  acr-pull-worker = {
    scope                            = "/subscriptions/fe31d3c8-576f-4c09-913c-635306834ff0/resourceGroups/rg-ocr-dev/providers/Microsoft.ContainerRegistry/registries/ee7c45crocrdev01"
    role_definition_name             = "AcrPull"
    workload_identity_key            = "worker"
    principal_type                   = "ServicePrincipal"
    skip_service_principal_aad_check = true
  }
  github-build-acr-push = {
    scope                            = "/subscriptions/fe31d3c8-576f-4c09-913c-635306834ff0/resourceGroups/rg-ocr-dev/providers/Microsoft.ContainerRegistry/registries/ee7c45crocrdev01"
    role_definition_name             = "AcrPush"
    principal_id                     = "9349a76e-8e56-49ad-9150-bfeda4d8e95b"
    principal_type                   = "ServicePrincipal"
    skip_service_principal_aad_check = true
  }
  github-build-acr-read = {
    scope                            = "/subscriptions/fe31d3c8-576f-4c09-913c-635306834ff0/resourceGroups/rg-ocr-dev/providers/Microsoft.ContainerRegistry/registries/ee7c45crocrdev01"
    role_definition_name             = "Reader"
    principal_id                     = "9349a76e-8e56-49ad-9150-bfeda4d8e95b"
    principal_type                   = "ServicePrincipal"
    skip_service_principal_aad_check = true
  }
  github-deploy-acr-pull = {
    scope                            = "/subscriptions/fe31d3c8-576f-4c09-913c-635306834ff0/resourceGroups/rg-ocr-dev/providers/Microsoft.ContainerRegistry/registries/ee7c45crocrdev01"
    role_definition_name             = "AcrPull"
    principal_id                     = "9349a76e-8e56-49ad-9150-bfeda4d8e95b"
    principal_type                   = "ServicePrincipal"
    skip_service_principal_aad_check = true
  }
  # github-deploy-acr-read = {
  #   scope                            = "/subscriptions/fe31d3c8-576f-4c09-913c-635306834ff0/resourceGroups/rg-ocr-dev/providers/Microsoft.ContainerRegistry/registries/ee7c45crocrdev01"
  #   role_definition_name             = "Reader"
  #   principal_id                     = "9349a76e-8e56-49ad-9150-bfeda4d8e95b"
  #   principal_type                   = "ServicePrincipal"
  #   skip_service_principal_aad_check = true
  # }
  github-deploy-container-apps = {
    scope                            = "/subscriptions/fe31d3c8-576f-4c09-913c-635306834ff0/resourceGroups/rg-ocr-dev"
    role_definition_name             = "Container Apps Contributor"
    principal_id                     = "9349a76e-8e56-49ad-9150-bfeda4d8e95b"
    principal_type                   = "ServicePrincipal"
    skip_service_principal_aad_check = true
  }

  langfuse-secrets-operator = {
    scope                = "/subscriptions/fe31d3c8-576f-4c09-913c-635306834ff0/resourceGroups/rg-ocr-dev/providers/Microsoft.KeyVault/vaults/ee7c45kvocrappdev01"
    role_definition_name = "Key Vault Secrets Officer"
    principal_id         = "c549ce05-71ca-4df3-b0e2-2863117e41fd"
    principal_type       = "User"
  }

  api-inbox = {
    scope                            = "/subscriptions/fe31d3c8-576f-4c09-913c-635306834ff0/resourceGroups/rg-ocr-dev/providers/Microsoft.Storage/storageAccounts/ee7c45stocrdocdev01/blobServices/default/containers/inbox"
    role_definition_name             = "Storage Blob Data Contributor"
    workload_identity_key            = "api"
    principal_type                   = "ServicePrincipal"
    skip_service_principal_aad_check = true
  }
  llmmagic-inbox = {
    scope                            = "/subscriptions/fe31d3c8-576f-4c09-913c-635306834ff0/resourceGroups/rg-ocr-dev/providers/Microsoft.Storage/storageAccounts/ee7c45stocrdocdev01/blobServices/default/containers/inbox"
    role_definition_name             = "Storage Blob Data Contributor"
    workload_identity_key            = "llmmagic"
    principal_type                   = "ServicePrincipal"
    skip_service_principal_aad_check = true
  }
  llmmagic-ocr-artifacts = {
    scope                            = "/subscriptions/fe31d3c8-576f-4c09-913c-635306834ff0/resourceGroups/rg-ocr-dev/providers/Microsoft.Storage/storageAccounts/ee7c45stocrdocdev01/blobServices/default/containers/ocr-artifacts"
    role_definition_name             = "Storage Blob Data Contributor"
    workload_identity_key            = "llmmagic"
    principal_type                   = "ServicePrincipal"
    skip_service_principal_aad_check = true
  }
  llmmagic-preprocessed = {
    scope                            = "/subscriptions/fe31d3c8-576f-4c09-913c-635306834ff0/resourceGroups/rg-ocr-dev/providers/Microsoft.Storage/storageAccounts/ee7c45stocrdocdev01/blobServices/default/containers/preprocessed"
    role_definition_name             = "Storage Blob Data Contributor"
    workload_identity_key            = "llmmagic"
    principal_type                   = "ServicePrincipal"
    skip_service_principal_aad_check = true
  }
  llmmagic-previews = {
    scope                            = "/subscriptions/fe31d3c8-576f-4c09-913c-635306834ff0/resourceGroups/rg-ocr-dev/providers/Microsoft.Storage/storageAccounts/ee7c45stocrdocdev01/blobServices/default/containers/previews"
    role_definition_name             = "Storage Blob Data Contributor"
    workload_identity_key            = "llmmagic"
    principal_type                   = "ServicePrincipal"
    skip_service_principal_aad_check = true
  }
  llmmagic-quarantine = {
    scope                            = "/subscriptions/fe31d3c8-576f-4c09-913c-635306834ff0/resourceGroups/rg-ocr-dev/providers/Microsoft.Storage/storageAccounts/ee7c45stocrdocdev01/blobServices/default/containers/quarantine"
    role_definition_name             = "Storage Blob Data Contributor"
    workload_identity_key            = "llmmagic"
    principal_type                   = "ServicePrincipal"
    skip_service_principal_aad_check = true
  }
  worker-archive = {
    scope                            = "/subscriptions/fe31d3c8-576f-4c09-913c-635306834ff0/resourceGroups/rg-ocr-dev/providers/Microsoft.Storage/storageAccounts/ee7c45stocrdocdev01/blobServices/default/containers/archive"
    role_definition_name             = "Storage Blob Data Contributor"
    workload_identity_key            = "worker"
    principal_type                   = "ServicePrincipal"
    skip_service_principal_aad_check = true
  }
  worker-inbox = {
    scope                            = "/subscriptions/fe31d3c8-576f-4c09-913c-635306834ff0/resourceGroups/rg-ocr-dev/providers/Microsoft.Storage/storageAccounts/ee7c45stocrdocdev01/blobServices/default/containers/inbox"
    role_definition_name             = "Storage Blob Data Contributor"
    workload_identity_key            = "worker"
    principal_type                   = "ServicePrincipal"
    skip_service_principal_aad_check = true
  }
  worker-ocr-artifacts = {
    scope                            = "/subscriptions/fe31d3c8-576f-4c09-913c-635306834ff0/resourceGroups/rg-ocr-dev/providers/Microsoft.Storage/storageAccounts/ee7c45stocrdocdev01/blobServices/default/containers/ocr-artifacts"
    role_definition_name             = "Storage Blob Data Contributor"
    workload_identity_key            = "worker"
    principal_type                   = "ServicePrincipal"
    skip_service_principal_aad_check = true
  }
  worker-preprocessed = {
    scope                            = "/subscriptions/fe31d3c8-576f-4c09-913c-635306834ff0/resourceGroups/rg-ocr-dev/providers/Microsoft.Storage/storageAccounts/ee7c45stocrdocdev01/blobServices/default/containers/preprocessed"
    role_definition_name             = "Storage Blob Data Contributor"
    workload_identity_key            = "worker"
    principal_type                   = "ServicePrincipal"
    skip_service_principal_aad_check = true
  }
  worker-previews = {
    scope                            = "/subscriptions/fe31d3c8-576f-4c09-913c-635306834ff0/resourceGroups/rg-ocr-dev/providers/Microsoft.Storage/storageAccounts/ee7c45stocrdocdev01/blobServices/default/containers/previews"
    role_definition_name             = "Storage Blob Data Contributor"
    workload_identity_key            = "worker"
    principal_type                   = "ServicePrincipal"
    skip_service_principal_aad_check = true
  }
  worker-quarantine = {
    scope                            = "/subscriptions/fe31d3c8-576f-4c09-913c-635306834ff0/resourceGroups/rg-ocr-dev/providers/Microsoft.Storage/storageAccounts/ee7c45stocrdocdev01/blobServices/default/containers/quarantine"
    role_definition_name             = "Storage Blob Data Contributor"
    workload_identity_key            = "worker"
    principal_type                   = "ServicePrincipal"
    skip_service_principal_aad_check = true
  }

  document-intelligence-storage-read = {
    scope                            = "/subscriptions/fe31d3c8-576f-4c09-913c-635306834ff0/resourceGroups/rg-ocr-dev/providers/Microsoft.Storage/storageAccounts/ee7c45stocrdocdev01"
    role_definition_name             = "Storage Blob Data Reader"
    principal_id                     = "c1954d28-deae-4d5e-b79a-012469238d68"
    principal_type                   = "ServicePrincipal"
    skip_service_principal_aad_check = true
  }
  llmmagic-document-intelligence = {
    scope                            = "/subscriptions/fe31d3c8-576f-4c09-913c-635306834ff0/resourceGroups/rg-ocr-dev/providers/Microsoft.CognitiveServices/accounts/ee7c45diocrdev01"
    role_definition_name             = "Cognitive Services User"
    workload_identity_key            = "llmmagic"
    principal_type                   = "ServicePrincipal"
    skip_service_principal_aad_check = true
  }
  llmmagic-foundry-user = {
    scope                            = "/subscriptions/fe31d3c8-576f-4c09-913c-635306834ff0/resourceGroups/rg-ocr-dev/providers/Microsoft.CognitiveServices/accounts/ais-ocr-dev-01"
    role_definition_name             = "Cognitive Services User"
    workload_identity_key            = "llmmagic"
    principal_type                   = "ServicePrincipal"
    skip_service_principal_aad_check = true
  }
  llmmagic-foundry-openai = {
    scope                            = "/subscriptions/fe31d3c8-576f-4c09-913c-635306834ff0/resourceGroups/rg-ocr-dev/providers/Microsoft.CognitiveServices/accounts/ais-ocr-dev-01"
    role_definition_name             = "Cognitive Services OpenAI User"
    workload_identity_key            = "llmmagic"
    principal_type                   = "ServicePrincipal"
    skip_service_principal_aad_check = true
  }

  dapr-api-send-document-processing = {
    scope                            = "/subscriptions/fe31d3c8-576f-4c09-913c-635306834ff0/resourceGroups/rg-ocr-dev/providers/Microsoft.ServiceBus/namespaces/ee7c45sbnsocrdev01/queues/sbq-ocr-dev-docproc-01"
    role_definition_name             = "Azure Service Bus Data Sender"
    workload_identity_key            = "dapr-servicebus-api"
    principal_type                   = "ServicePrincipal"
    skip_service_principal_aad_check = true
  }
  dapr-api-receive-processing-results = {
    scope                            = "/subscriptions/fe31d3c8-576f-4c09-913c-635306834ff0/resourceGroups/rg-ocr-dev/providers/Microsoft.ServiceBus/namespaces/ee7c45sbnsocrdev01/queues/sbq-ocr-dev-procres-01"
    role_definition_name             = "Azure Service Bus Data Receiver"
    workload_identity_key            = "dapr-servicebus-api"
    principal_type                   = "ServicePrincipal"
    skip_service_principal_aad_check = true
  }
  dapr-worker-receive-document-processing = {
    scope                            = "/subscriptions/fe31d3c8-576f-4c09-913c-635306834ff0/resourceGroups/rg-ocr-dev/providers/Microsoft.ServiceBus/namespaces/ee7c45sbnsocrdev01/queues/sbq-ocr-dev-docproc-01"
    role_definition_name             = "Azure Service Bus Data Receiver"
    workload_identity_key            = "dapr-servicebus-worker"
    principal_type                   = "ServicePrincipal"
    skip_service_principal_aad_check = true
  }
  dapr-worker-send-processing-results = {
    scope                            = "/subscriptions/fe31d3c8-576f-4c09-913c-635306834ff0/resourceGroups/rg-ocr-dev/providers/Microsoft.ServiceBus/namespaces/ee7c45sbnsocrdev01/queues/sbq-ocr-dev-procres-01"
    role_definition_name             = "Azure Service Bus Data Sender"
    workload_identity_key            = "dapr-servicebus-worker"
    principal_type                   = "ServicePrincipal"
    skip_service_principal_aad_check = true
  }
}
