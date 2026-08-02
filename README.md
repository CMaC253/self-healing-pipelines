# Self-Healing Azure Pipelines Workflow

A complete reference implementation that automatically troubleshoots failed Azure DevOps pipelines using AI agents + the Azure DevOps MCP server, opens pull requests with fixes when needed, and notifies Slack/Teams.

## Infrastructure (Terraform)
- Provision infra using `terraform init` and `terraform apply` in the `infra/` directory.
- Resources created: Resource Group, Managed Identity, Storage Account, Cosmos DB, Key Vault, Function App (Premium EP1), and Azure OpenAI role assignments.

## Setup
1. Provision infra using Terraform.
2. The Terraform script will automatically seed Key Vault secrets from your variables.
3. Deploy function code: `func azure functionapp publish <func-name> --python`
4. Configure Service Hook in Azure DevOps UI (Build completed -> Web hook pointing to the Function URL).
