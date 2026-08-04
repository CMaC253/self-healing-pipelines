TERRAFORM_SKILL = """
TERRAFORM EXPERT MODE ENGAGED:
- If the error is a state lock: DO NOT delete the state. Use the MCP tools to propose running 'terraform force-unlock <LOCK_ID>' as a pipeline variable update, or document it for the user.
- If the error is a missing provider: Ensure the `required_providers` block in the root `main.tf` is updated.
- If the error is a syntax error: Use `terraform fmt` and `terraform validate` mental models. 
- NEVER change resource names (e.g., 'azurerm_resource_group.main') as this will destroy and recreate infrastructure. Always append or modify attributes.
"""
