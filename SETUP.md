# Setup & Deployment Guide (Updated Aug 2026)

## Prerequisites
1. **Azure Subscription** with permissions to create Resource Groups, Function Apps, Cosmos DB, Key Vault, and Managed Identities.
2. **Azure AI Foundry Resource**: Pre-existing Azure AI Foundry hub with a deployed **GPT-5** (or GPT-5-mini) model.
3. **Azure DevOps Project** containing the codebase and pipelines you want to monitor.
4. **Azure Resource Manager Service Connection**: Create a service connection in ADO named `azure-sub` with contributor access to your Azure subscription.
5. **Azure DevOps PAT**: A Personal Access Token with `Code (Read & Write)` and `Build (Read)` scopes.
6. **Terraform Backend Storage**: An existing Azure Storage Account to hold your Terraform state file.

## Deployment Steps

### Step 1: Configure Pipeline Variables
In your Azure DevOps project, go to **Pipelines -> Library** and create a variable group named `self-healing-secrets`. Add the following variables:
* `ADO_PAT`: Your Azure DevOps Personal Access Token.
* `OPENAI_NAME`: Name of your Azure AI Foundry resource.
* `OPENAI_RG`: Resource Group of your Azure AI Foundry resource.
* `OPENAI_DEPLOYMENT`: The deployment name of your LLM (e.g., `gpt-5`).
* `MCP_SERVER_URL`: The URL where your Azure DevOps MCP Server is hosted.
* `SLACK_WEBHOOK`: Your Slack or Teams incoming webhook URL.
* `ARM_CLIENT_ID`, `ARM_CLIENT_SECRET`, `ARM_SUBSCRIPTION_ID`, `ARM_TENANT_ID`: Service Principal credentials for Terraform.
* `tf_state_storage`, `tf_state_rg`, `tf_state_access_key`: Storage account details for Terraform state.

### Step 2: Run the CI/CD Pipeline
The repository contains an `azure-pipelines.yml` file. 
1. Commit and push this code to your `main` branch.
2. Azure DevOps will automatically detect the pipeline.
3. Run the pipeline. It will execute `terraform apply` to provision the Azure Function, Cosmos DB, Key Vault, and Managed Identity. It will then deploy the Python 3.12 code to the Azure Function App.

### Step 3: Deploy the MCP Server (One-time setup)
Host the official Azure DevOps MCP server as a container on Azure Container Apps. Run the following Azure CLI command:

    az containerapp create \
      --name mcp-shp \
      --resource-group rg-shp \
      --image mcr.microsoft.com/devcontainers/azure-devops-mcp:latest \
      --ingress external --target-port 3000 \
      --env-vars ADO_ORG=myorg ADO_PAT_SECRET_URI=<key_vault_secret_uri>

Take the generated FQDN of this container app and set it as the `MCP_SERVER_URL` variable in your ADO Pipeline Library.

### Step 4: Wire the Service Hook (Trigger)
Once the CI/CD pipeline finishes and the Azure Function is deployed:
1. In your Azure DevOps Project, go to **Project Settings -> Service Hooks**.
2. Click **+ Create subscription** and select **Web hook**.
3. Configure the trigger:
   * **Event:** Build completed
   * **Filter:** Specific pipelines, `Status = failed`
4. Set the **URL** to your Azure Function's endpoint. The format should be:
   `https://func-shp.azurewebsites.net/api/pipeline-failed?code=<YOUR_FUNCTION_KEY>`
   *(Get the function key from the Azure Portal -> Function App -> App Keys).*
5. Click **Test** to send a test payload.

### Step 5: Test the Workflow
1. Ensure the repository you are testing against is listed in the `allowed_repos` variable in `infra/variables.tf`.
2. Deliberately break a pipeline in that repository (e.g., introduce a YAML syntax error or a missing variable).
3. Run the pipeline and let it fail.
4. Check the logs in the Azure Function App (`func-shp`). You should see the GPT-5 agent retrieve the logs, route to the correct Expert Skill, and either open a PR or send a Slack/Teams alert!
EOF~
cat << 'EOF' > SETUP.md
# Setup & Deployment Guide (Updated Aug 2026)

## Prerequisites
1. **Azure Subscription** with permissions to create Resource Groups, Function Apps, Cosmos DB, Key Vault, and Managed Identities.
2. **Azure AI Foundry Resource**: Pre-existing Azure AI Foundry hub with a deployed **GPT-5** (or GPT-5-mini) model.
3. **Azure DevOps Project** containing the codebase and pipelines you want to monitor.
4. **Azure Resource Manager Service Connection**: Create a service connection in ADO named `azure-sub` with contributor access to your Azure subscription.
5. **Azure DevOps PAT**: A Personal Access Token with `Code (Read & Write)` and `Build (Read)` scopes.
6. **Terraform Backend Storage**: An existing Azure Storage Account to hold your Terraform state file.

## Deployment Steps

### Step 1: Configure Pipeline Variables
In your Azure DevOps project, go to **Pipelines -> Library** and create a variable group named `self-healing-secrets`. Add the following variables:
* `ADO_PAT`: Your Azure DevOps Personal Access Token.
* `OPENAI_NAME`: Name of your Azure AI Foundry resource.
* `OPENAI_RG`: Resource Group of your Azure AI Foundry resource.
* `OPENAI_DEPLOYMENT`: The deployment name of your LLM (e.g., `gpt-5`).
* `MCP_SERVER_URL`: The URL where your Azure DevOps MCP Server is hosted.
* `SLACK_WEBHOOK`: Your Slack or Teams incoming webhook URL.
* `ARM_CLIENT_ID`, `ARM_CLIENT_SECRET`, `ARM_SUBSCRIPTION_ID`, `ARM_TENANT_ID`: Service Principal credentials for Terraform.
* `tf_state_storage`, `tf_state_rg`, `tf_state_access_key`: Storage account details for Terraform state.

### Step 2: Run the CI/CD Pipeline
The repository contains an `azure-pipelines.yml` file. 
1. Commit and push this code to your `main` branch.
2. Azure DevOps will automatically detect the pipeline.
3. Run the pipeline. It will execute `terraform apply` to provision the Azure Function, Cosmos DB, Key Vault, and Managed Identity. It will then deploy the Python 3.12 code to the Azure Function App.

### Step 3: Deploy the MCP Server (One-time setup)
Host the official Azure DevOps MCP server as a container on Azure Container Apps. Run the following Azure CLI command:

    az containerapp create \
      --name mcp-shp \
      --resource-group rg-shp \
      --image mcr.microsoft.com/devcontainers/azure-devops-mcp:latest \
      --ingress external --target-port 3000 \
      --env-vars ADO_ORG=myorg ADO_PAT_SECRET_URI=<key_vault_secret_uri>

Take the generated FQDN of this container app and set it as the `MCP_SERVER_URL` variable in your ADO Pipeline Library.

### Step 4: Wire the Service Hook (Trigger)
Once the CI/CD pipeline finishes and the Azure Function is deployed:
1. In your Azure DevOps Project, go to **Project Settings -> Service Hooks**.
2. Click **+ Create subscription** and select **Web hook**.
3. Configure the trigger:
   * **Event:** Build completed
   * **Filter:** Specific pipelines, `Status = failed`
4. Set the **URL** to your Azure Function's endpoint. The format should be:
   `https://func-shp.azurewebsites.net/api/pipeline-failed?code=<YOUR_FUNCTION_KEY>`
   *(Get the function key from the Azure Portal -> Function App -> App Keys).*
5. Click **Test** to send a test payload.

### Step 5: Test the Workflow
1. Ensure the repository you are testing against is listed in the `allowed_repos` variable in `infra/variables.tf`.
2. Deliberately break a pipeline in that repository (e.g., introduce a YAML syntax error or a missing variable).
3. Run the pipeline and let it fail.
4. Check the logs in the Azure Function App (`func-shp`). You should see the GPT-5 agent retrieve the logs, route to the correct Expert Skill, and either open a PR or send a Slack/Teams alert!
