variable "base_name" {
  type        = string
  description = "Base name for resources"
  default     = "shp"
}

variable "location" {
  type        = string
  description = "Azure region for all resources"
  default     = "eastus"
}

variable "ado_org" {
  type        = string
  description = "Azure DevOps organization name"
}

variable "ado_pat" {
  type        = string
  description = "Azure DevOps Personal Access Token"
  sensitive   = true
}

variable "openai_name" {
  type        = string
  description = "Name of the pre-existing Azure OpenAI account"
}

variable "openai_resource_group_name" {
  type        = string
  description = "Resource Group of the pre-existing Azure OpenAI account"
}

variable "openai_deployment" {
  type        = string
  description = "Deployment name inside Azure OpenAI"
}

variable "mcp_server_url" {
  type        = string
  description = "URL of the hosted Azure DevOps MCP server"
}

variable "slack_webhook" {
  type        = string
  description = "Slack or Teams webhook URL"
  sensitive   = true
}

variable "allowed_repos" {
  type        = list(string)
  description = "List of allowed repositories in format org/repo"
  default     = ["myorg/repo-a", "myorg/repo-b"]
}
