import requests, logging
from config import cfg

class McpClient:
    def __init__(self):
        self.url = cfg.mcp_server_url

    def list_tools(self):
        return self._call("tools/list", {})

    def call_tool(self, name: str, arguments: dict):
        return self._call("tools/call", {"name": name, "arguments": arguments})

    def _call(self, method: str, params: dict):
        r = requests.post(
            self.url,
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {cfg.ado_pat}"},
            json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
            timeout=120,
        )
        r.raise_for_status()
        return r.json().get("result")
