subscription_id                 = "16060ea2-28be-4b09-8e6d-060249d69ddd"
application_resource_group_name = "rg-ocr-dev-arksab"

# Existing UAI resources. RBAC reads their principal IDs automatically.
workload_identities = {
  web                    = { name = "id-ocr-web-dev" }
  api                    = { name = "id-ocr-api-dev" }
  api-migrator           = { name = "id-ocr-api-migrator-dev" }
  dapr-servicebus-api    = { name = "id-ocr-dapr-sb-api-dev" }
  dapr-servicebus-worker = { name = "id-ocr-dapr-sb-worker-dev" }
  llmmagic               = { name = "id-ocr-llmmagic-dev" }
  worker                 = { name = "id-ocr-worker-dev" }
}

role_assignments = {
  acr-pull-web = {
    scope                            = "/subscriptions/16060ea2-28be-4b09-8e6d-060249d69ddd/resourceGroups/rg-ocr-dev-arksab/providers/Microsoft.ContainerRegistry/registries/acrocrdevarksab01"
    role_definition_name             = "AcrPull"
    workload_identity_key            = "web"
    principal_type                   = "ServicePrincipal"
    skip_service_principal_aad_check = true
  }
  acr-pull-api = {
    scope                            = "/subscriptions/16060ea2-28be-4b09-8e6d-060249d69ddd/resourceGroups/rg-ocr-dev-arksab/providers/Microsoft.ContainerRegistry/registries/acrocrdevarksab01"
    role_definition_name             = "AcrPull"
    workload_identity_key            = "api"
    principal_type                   = "ServicePrincipal"
    skip_service_principal_aad_check = true
  }
  acr-pull-api-migrator = {
    scope                            = "/subscriptions/16060ea2-28be-4b09-8e6d-060249d69ddd/resourceGroups/rg-ocr-dev-arksab/providers/Microsoft.ContainerRegistry/registries/acrocrdevarksab01"
    role_definition_name             = "AcrPull"
    workload_identity_key            = "api-migrator"
    principal_type                   = "ServicePrincipal"
    skip_service_principal_aad_check = true
  }
  acr-pull-llmmagic = {
    scope                            = "/subscriptions/16060ea2-28be-4b09-8e6d-060249d69ddd/resourceGroups/rg-ocr-dev-arksab/providers/Microsoft.ContainerRegistry/registries/acrocrdevarksab01"
    role_definition_name             = "AcrPull"
    workload_identity_key            = "llmmagic"
    principal_type                   = "ServicePrincipal"
    skip_service_principal_aad_check = true
  }
  acr-pull-worker = {
    scope                            = "/subscriptions/16060ea2-28be-4b09-8e6d-060249d69ddd/resourceGroups/rg-ocr-dev-arksab/providers/Microsoft.ContainerRegistry/registries/acrocrdevarksab01"
    role_definition_name             = "AcrPull"
    workload_identity_key            = "worker"
    principal_type                   = "ServicePrincipal"
    skip_service_principal_aad_check = true
  }

  api-inbox = {
    scope                            = "/subscriptions/16060ea2-28be-4b09-8e6d-060249d69ddd/resourceGroups/rg-ocr-dev-arksab/providers/Microsoft.Storage/storageAccounts/stocrdevarksab01/blobServices/default/containers/inbox"
    role_definition_name             = "Storage Blob Data Contributor"
    workload_identity_key            = "api"
    principal_type                   = "ServicePrincipal"
    skip_service_principal_aad_check = true
  }
  llmmagic-inbox = {
    scope                            = "/subscriptions/16060ea2-28be-4b09-8e6d-060249d69ddd/resourceGroups/rg-ocr-dev-arksab/providers/Microsoft.Storage/storageAccounts/stocrdevarksab01/blobServices/default/containers/inbox"
    role_definition_name             = "Storage Blob Data Contributor"
    workload_identity_key            = "llmmagic"
    principal_type                   = "ServicePrincipal"
    skip_service_principal_aad_check = true
  }
  llmmagic-ocr-artifacts = {
    scope                            = "/subscriptions/16060ea2-28be-4b09-8e6d-060249d69ddd/resourceGroups/rg-ocr-dev-arksab/providers/Microsoft.Storage/storageAccounts/stocrdevarksab01/blobServices/default/containers/ocr-artifacts"
    role_definition_name             = "Storage Blob Data Contributor"
    workload_identity_key            = "llmmagic"
    principal_type                   = "ServicePrincipal"
    skip_service_principal_aad_check = true
  }
  llmmagic-preprocessed = {
    scope                            = "/subscriptions/16060ea2-28be-4b09-8e6d-060249d69ddd/resourceGroups/rg-ocr-dev-arksab/providers/Microsoft.Storage/storageAccounts/stocrdevarksab01/blobServices/default/containers/preprocessed"
    role_definition_name             = "Storage Blob Data Contributor"
    workload_identity_key            = "llmmagic"
    principal_type                   = "ServicePrincipal"
    skip_service_principal_aad_check = true
  }
  llmmagic-previews = {
    scope                            = "/subscriptions/16060ea2-28be-4b09-8e6d-060249d69ddd/resourceGroups/rg-ocr-dev-arksab/providers/Microsoft.Storage/storageAccounts/stocrdevarksab01/blobServices/default/containers/previews"
    role_definition_name             = "Storage Blob Data Contributor"
    workload_identity_key            = "llmmagic"
    principal_type                   = "ServicePrincipal"
    skip_service_principal_aad_check = true
  }
  llmmagic-quarantine = {
    scope                            = "/subscriptions/16060ea2-28be-4b09-8e6d-060249d69ddd/resourceGroups/rg-ocr-dev-arksab/providers/Microsoft.Storage/storageAccounts/stocrdevarksab01/blobServices/default/containers/quarantine"
    role_definition_name             = "Storage Blob Data Contributor"
    workload_identity_key            = "llmmagic"
    principal_type                   = "ServicePrincipal"
    skip_service_principal_aad_check = true
  }
  worker-archive = {
    scope                            = "/subscriptions/16060ea2-28be-4b09-8e6d-060249d69ddd/resourceGroups/rg-ocr-dev-arksab/providers/Microsoft.Storage/storageAccounts/stocrdevarksab01/blobServices/default/containers/archive"
    role_definition_name             = "Storage Blob Data Contributor"
    workload_identity_key            = "worker"
    principal_type                   = "ServicePrincipal"
    skip_service_principal_aad_check = true
  }
  worker-inbox = {
    scope                            = "/subscriptions/16060ea2-28be-4b09-8e6d-060249d69ddd/resourceGroups/rg-ocr-dev-arksab/providers/Microsoft.Storage/storageAccounts/stocrdevarksab01/blobServices/default/containers/inbox"
    role_definition_name             = "Storage Blob Data Contributor"
    workload_identity_key            = "worker"
    principal_type                   = "ServicePrincipal"
    skip_service_principal_aad_check = true
  }
  worker-ocr-artifacts = {
    scope                            = "/subscriptions/16060ea2-28be-4b09-8e6d-060249d69ddd/resourceGroups/rg-ocr-dev-arksab/providers/Microsoft.Storage/storageAccounts/stocrdevarksab01/blobServices/default/containers/ocr-artifacts"
    role_definition_name             = "Storage Blob Data Contributor"
    workload_identity_key            = "worker"
    principal_type                   = "ServicePrincipal"
    skip_service_principal_aad_check = true
  }
  worker-preprocessed = {
    scope                            = "/subscriptions/16060ea2-28be-4b09-8e6d-060249d69ddd/resourceGroups/rg-ocr-dev-arksab/providers/Microsoft.Storage/storageAccounts/stocrdevarksab01/blobServices/default/containers/preprocessed"
    role_definition_name             = "Storage Blob Data Contributor"
    workload_identity_key            = "worker"
    principal_type                   = "ServicePrincipal"
    skip_service_principal_aad_check = true
  }
  worker-previews = {
    scope                            = "/subscriptions/16060ea2-28be-4b09-8e6d-060249d69ddd/resourceGroups/rg-ocr-dev-arksab/providers/Microsoft.Storage/storageAccounts/stocrdevarksab01/blobServices/default/containers/previews"
    role_definition_name             = "Storage Blob Data Contributor"
    workload_identity_key            = "worker"
    principal_type                   = "ServicePrincipal"
    skip_service_principal_aad_check = true
  }
  worker-quarantine = {
    scope                            = "/subscriptions/16060ea2-28be-4b09-8e6d-060249d69ddd/resourceGroups/rg-ocr-dev-arksab/providers/Microsoft.Storage/storageAccounts/stocrdevarksab01/blobServices/default/containers/quarantine"
    role_definition_name             = "Storage Blob Data Contributor"
    workload_identity_key            = "worker"
    principal_type                   = "ServicePrincipal"
    skip_service_principal_aad_check = true
  }

  document-intelligence-storage-read = {
    scope                            = "/subscriptions/16060ea2-28be-4b09-8e6d-060249d69ddd/resourceGroups/rg-ocr-dev-arksab/providers/Microsoft.Storage/storageAccounts/stocrdevarksab01"
    role_definition_name             = "Storage Blob Data Reader"
    principal_id                     = "4da04c1d-529c-42e7-82bf-7762d0fa55f3"
    principal_type                   = "ServicePrincipal"
    skip_service_principal_aad_check = true
  }
  llmmagic-document-intelligence = {
    scope                            = "/subscriptions/16060ea2-28be-4b09-8e6d-060249d69ddd/resourceGroups/rg-ocr-dev-arksab/providers/Microsoft.CognitiveServices/accounts/di-ocr-dev-arksab"
    role_definition_name             = "Cognitive Services User"
    workload_identity_key            = "llmmagic"
    principal_type                   = "ServicePrincipal"
    skip_service_principal_aad_check = true
  }
  llmmagic-foundry-user = {
    scope                            = "/subscriptions/16060ea2-28be-4b09-8e6d-060249d69ddd/resourceGroups/rg-ocr-dev-arksab/providers/Microsoft.CognitiveServices/accounts/ai-ocr-dev-arksab1"
    role_definition_name             = "Cognitive Services User"
    workload_identity_key            = "llmmagic"
    principal_type                   = "ServicePrincipal"
    skip_service_principal_aad_check = true
  }
  llmmagic-foundry-openai = {
    scope                            = "/subscriptions/16060ea2-28be-4b09-8e6d-060249d69ddd/resourceGroups/rg-ocr-dev-arksab/providers/Microsoft.CognitiveServices/accounts/ai-ocr-dev-arksab1"
    role_definition_name             = "Cognitive Services OpenAI User"
    workload_identity_key            = "llmmagic"
    principal_type                   = "ServicePrincipal"
    skip_service_principal_aad_check = true
  }

  dapr-api-send-document-processing = {
    scope                            = "/subscriptions/16060ea2-28be-4b09-8e6d-060249d69ddd/resourceGroups/rg-ocr-dev-arksab/providers/Microsoft.ServiceBus/namespaces/sb-ocr-dev-arksab/queues/document-processing"
    role_definition_name             = "Azure Service Bus Data Sender"
    workload_identity_key            = "dapr-servicebus-api"
    principal_type                   = "ServicePrincipal"
    skip_service_principal_aad_check = true
  }
  dapr-api-receive-processing-results = {
    scope                            = "/subscriptions/16060ea2-28be-4b09-8e6d-060249d69ddd/resourceGroups/rg-ocr-dev-arksab/providers/Microsoft.ServiceBus/namespaces/sb-ocr-dev-arksab/queues/processing-results"
    role_definition_name             = "Azure Service Bus Data Receiver"
    workload_identity_key            = "dapr-servicebus-api"
    principal_type                   = "ServicePrincipal"
    skip_service_principal_aad_check = true
  }
  dapr-worker-receive-document-processing = {
    scope                            = "/subscriptions/16060ea2-28be-4b09-8e6d-060249d69ddd/resourceGroups/rg-ocr-dev-arksab/providers/Microsoft.ServiceBus/namespaces/sb-ocr-dev-arksab/queues/document-processing"
    role_definition_name             = "Azure Service Bus Data Receiver"
    workload_identity_key            = "dapr-servicebus-worker"
    principal_type                   = "ServicePrincipal"
    skip_service_principal_aad_check = true
  }
  dapr-worker-send-processing-results = {
    scope                            = "/subscriptions/16060ea2-28be-4b09-8e6d-060249d69ddd/resourceGroups/rg-ocr-dev-arksab/providers/Microsoft.ServiceBus/namespaces/sb-ocr-dev-arksab/queues/processing-results"
    role_definition_name             = "Azure Service Bus Data Sender"
    workload_identity_key            = "dapr-servicebus-worker"
    principal_type                   = "ServicePrincipal"
    skip_service_principal_aad_check = true
  }

  # The same OIDC service principal is used by Application build and deploy in this POC.
  github-application-acr-push = {
    scope                            = "/subscriptions/16060ea2-28be-4b09-8e6d-060249d69ddd/resourceGroups/rg-ocr-dev-arksab/providers/Microsoft.ContainerRegistry/registries/acrocrdevarksab01"
    role_definition_name             = "AcrPush"
    principal_id                     = "8fc1b08a-0460-4139-a393-7ab120f70e33"
    principal_type                   = "ServicePrincipal"
    skip_service_principal_aad_check = true
  }
  github-application-acr-reader = {
    scope                            = "/subscriptions/16060ea2-28be-4b09-8e6d-060249d69ddd/resourceGroups/rg-ocr-dev-arksab/providers/Microsoft.ContainerRegistry/registries/acrocrdevarksab01"
    role_definition_name             = "Reader"
    principal_id                     = "8fc1b08a-0460-4139-a393-7ab120f70e33"
    principal_type                   = "ServicePrincipal"
    skip_service_principal_aad_check = true
  }
  github-application-container-apps = {
    scope                            = "/subscriptions/16060ea2-28be-4b09-8e6d-060249d69ddd/resourceGroups/rg-ocr-dev-arksab"
    role_definition_name             = "Container Apps Contributor"
    principal_id                     = "8fc1b08a-0460-4139-a393-7ab120f70e33"
    principal_type                   = "ServicePrincipal"
    skip_service_principal_aad_check = true
  }
}
