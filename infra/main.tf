terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.100"
    }
  }
}

provider "azurerm" {
  features {}
}

resource "azurerm_resource_group" "rg" {
  name     = "rg-${var.base_name}"
  location = var.location
}

# Managed Identity
resource "azurerm_user_assigned_identity" "mi" {
  name                = "mi-${var.base_name}"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
}

# Storage Account for Function
resource "azurerm_storage_account" "storage" {
  name                     = "st${replace(var.base_name, "-", "")}"
  resource_group_name      = azurerm_resource_group.rg.name
  location                 = azurerm_resource_group.rg.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
}

# Cosmos DB
resource "azurerm_cosmosdb_account" "cosmos" {
  name                = "cosmos-${var.base_name}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  offer_type          = "Standard"
  kind                = "GlobalDocumentDB"

  consistency_policy {
    consistency_level       = "Session"
    max_interval_in_seconds = 5
    max_staleness_prefix    = 100
  }

  geo_location {
    location          = azurerm_resource_group.rg.location
    failover_priority = 0
  }
}

resource "azurerm_cosmosdb_sql_database" "db" {
  name                = "selfhealing"
  resource_group_name = azurerm_resource_group.rg.name
  account_name        = azurerm_cosmosdb_account.cosmos.name
  throughput          = 400
}

resource "azurerm_cosmosdb_sql_container" "container" {
  name                  = "attempts"
  resource_group_name   = azurerm_resource_group.rg.name
  account_name          = azurerm_cosmosdb_account.cosmos.name
  database_name         = azurerm_cosmosdb_sql_database.db.name
  partition_key_path    = "/pipelineId"
  partition_key_version = 1
  throughput            = 400
}

# Key Vault
resource "azurerm_key_vault" "kv" {
  name                       = "kv-${var.base_name}"
  location                   = azurerm_resource_group.rg.location
  resource_group_name        = azurerm_resource_group.rg.name
  tenant_id                  = data.azurerm_client_config.current.tenant_id
  sku_name                   = "standard"
  soft_delete_retention_days = 7
  purge_protection_enabled   = false
}

resource "azurerm_key_vault_access_policy" "mi_access" {
  key_vault_id = azurerm_key_vault.kv.id
  tenant_id    = data.azurerm_client_config.current.tenant_id
  object_id    = azurerm_user_assigned_identity.mi.principal_id

  secret_permissions = [
    "Get", "List"
  ]
}

resource "azurerm_key_vault_secret" "ado_pat" {
  name         = "ado-pat"
  value        = var.ado_pat
  key_vault_id = azurerm_key_vault.kv.id
}

resource "azurerm_key_vault_secret" "slack_webhook" {
  name         = "slack-webhook"
  value        = var.slack_webhook
  key_vault_id = azurerm_key_vault.kv.id
}

# Azure OpenAI Role Assignment
data "azurerm_cognitive_account" "openai" {
  name                = var.openai_name
  resource_group_name = var.openai_resource_group_name
}

resource "azurerm_role_assignment" "openai_role" {
  scope                = data.azurerm_cognitive_account.openai.id
  role_definition_name = "Cognitive Services OpenAI User"
  principal_id         = azurerm_user_assigned_identity.mi.principal_id
}

# App Service Plan (Premium EP1 for VNet integration & always-on capabilities)
resource "azurerm_service_plan" "plan" {
  name                = "plan-${var.base_name}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  os_type             = "Linux"
  sku_name            = "EP1"
}

# Function App
resource "azurerm_linux_function_app" "func" {
  name                       = "func-${var.base_name}"
  location                   = azurerm_resource_group.rg.location
  resource_group_name        = azurerm_resource_group.rg.name
  service_plan_id            = azurerm_service_plan.plan.id
  storage_account_name       = azurerm_storage_account.storage.name
  storage_account_access_key = azurerm_storage_account.storage.primary_access_key

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.mi.id]
  }

  app_settings = {
    "AZURE_TENANT_ID"             = data.azurerm_client_config.current.tenant_id
    "ADO_ORG"                     = var.ado_org
    "ADO_PAT_SECRET_URI"          = azurerm_key_vault_secret.ado_pat.id
    "OPENAI_NAME"                 = var.openai_name
    "OPENAI_DEPLOYMENT"           = var.openai_deployment
    "MCP_SERVER_URL"              = var.mcp_server_url
    "SLACK_WEBHOOK_SECRET_URI"    = azurerm_key_vault_secret.slack_webhook.id
    "COSMOS_ENDPOINT"             = azurerm_cosmosdb_account.cosmos.endpoint
    "COSMOS_DB"                   = "selfhealing"
    "COSMOS_CONTAINER"            = "attempts"
    "MAX_ATTEMPTS_PER_PIPELINE"   = "3"
    "COOLDOWN_MINUTES"            = "60"
    "ALLOWED_REPOS"               = jsonencode(var.allowed_repos)
  }

  site_config {
    application_stack {
      python_version = "3.11"
    }
  }
}
