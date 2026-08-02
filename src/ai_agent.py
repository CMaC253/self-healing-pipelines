import json, logging
from openai import AzureOpenAI
from config import cfg
from mcp_client import McpClient
from prompts.system_prompt import SYSTEM_PROMPT

class SelfHealingAgent:
    def __init__(self):
        self.client = AzureOpenAI(
            azure_endpoint=f"https://{cfg.openai_name}.openai.azure.com",
            api_version="2024-10-21",
            azure_ad_token_provider=lambda: cfg.credential.get_token("https://cognitiveservices.azure.com/.default").token,
        )
        self.mcp = McpClient()

    def _tools(self):
        mcp_tools = self.mcp.list_tools() or []
        return [{
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t.get("description", ""),
                "parameters": t.get("inputSchema", {"type": "object", "properties": {}}),
            },
        } for t in mcp_tools]

    def run(self, build_id: int, project: str, failure_context: dict) -> dict:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": (
                f"Pipeline build {build_id} in project '{project}' failed.\n\n"
                f"Failure context:\n```json\n{json.dumps(failure_context, indent=2)}\n```\n\n"
                f"Diagnose the root cause. If a code change will fix it, "
                f"use the MCP tools to inspect the repo, create a branch, commit the fix, "
                f"and open a pull request. Return a JSON summary."
            )},
        ]

        for _ in range(10):  # max reasoning loops
            resp = self.client.chat.completions.create(
                model=cfg.openai_deployment,
                messages=messages,
                tools=self._tools(),
                tool_choice="auto",
                temperature=0.1,
            )
            msg = resp.choices[0].message
            messages.append(msg)

            if not msg.tool_calls:
                return self._parse_summary(msg.content)

            for tc in msg.tool_calls:
                args = json.loads(tc.function.arguments or "{}")
                logging.info(f"Tool call: {tc.function.name} args={args}")
                result = self.mcp.call_tool(tc.function.name, args)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result),
                })

        return {"root_cause": "Max iterations reached", "pr_url": None, "summary": "Could not converge"}

    @staticmethod
    def _parse_summary(content: str) -> dict:
        try:
            return json.loads(content)
        except Exception:
            return {"root_cause": content, "pr_url": None, "summary": content}
