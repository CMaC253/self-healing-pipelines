import json, logging
from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import UserMessage, SystemMessage, AssistantMessage, ToolMessage, ToolDefinition
from azure.identity import DefaultAzureCredential
from config import cfg
from mcp_client import McpClient
from prompts.base_prompt import BASE_PROMPT

class SelfHealingAgent:
    def __init__(self, system_prompt: str = BASE_PROMPT):
        # Using the unified Azure AI Inference SDK standard as of 2026
        credential = DefaultAzureCredential()
        self.client = ChatCompletionsClient(
            endpoint=cfg.openai_endpoint,
            credential=credential,
            api_version="2026-07-01-preview"
        )
        self.mcp = McpClient()
        self.system_prompt = system_prompt

    def _tools(self):
        mcp_tools = self.mcp.list_tools() or []
        tools = []
        for t in mcp_tools:
            schema = t.get("inputSchema", {"type": "object", "properties": {}})
            if not isinstance(schema, dict):
                schema = {"type": "object", "properties": {}}
                
            tools.append(ToolDefinition(
                name=t["name"],
                description=t.get("description", ""),
                parameters=schema
            ))
        return tools

    def run(self, build_id: int, project: str, failure_context: dict) -> dict:
        # GPT-5 deployment name (e.g., "gpt-5" or "gpt-5-mini")
        model_name = cfg.openai_deployment

        messages = [
            SystemMessage(content=self.system_prompt),
            UserMessage(content=(
                f"Pipeline build {build_id} in project '{project}' failed.\n\n"
                f"Failure context:\n```json\n{json.dumps(failure_context, indent=2)}\n```\n\n"
                f"Diagnose the root cause. If a code change will fix it, "
                f"use the MCP tools to inspect the repo, create a branch, commit the fix, "
                f"and open a pull request. Return a JSON summary."
            ))
        ]

        for _ in range(10):  # max reasoning loops
            resp = self.client.complete(
                model=model_name,
                messages=messages,
                tools=self._tools(),
                tool_choice="auto",
                temperature=0.1, # GPT-5 responds well to low temp for strict JSON output
            )
            
            msg = resp.choices[0].message
            messages.append(AssistantMessage(content=msg.content, tool_calls=msg.tool_calls))

            if not msg.tool_calls:
                return self._parse_summary(msg.content)

            for tc in msg.tool_calls:
                args = json.loads(tc.function.arguments or "{}")
                logging.info(f"Tool call: {tc.function.name} args={args}")
                
                result = self.mcp.call_tool(tc.function.name, args)
                messages.append(ToolMessage(
                    tool_call_id=tc.id,
                    content=json.dumps(result)
                ))

        return {"root_cause": "Max iterations reached", "pr_url": None, "summary": "Could not converge"}

    @staticmethod
    def _parse_summary(content: str) -> dict:
        try:
            return json.loads(content)
        except Exception:
            return {"root_cause": content, "pr_url": None, "summary": content, "confidence_score": 0}
