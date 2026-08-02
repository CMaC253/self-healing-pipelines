import os, json
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

_credential = DefaultAzureCredential()

def _kv_secret(uri: str) -> str:
    if not uri:
        return ""
    # uri form: https://<vault>.vault.azure.net/secrets/<name>/<version>
    vault = uri.split("//")[1].split(".")[0]
    name = uri.rstrip("/").split("/")[-2]
    client = SecretClient(f"https://{vault}.vault.azure.net", _credential)
    return client.get_secret(name).value

class Config:
    ado_org = os.environ["ADO_ORG"]
    ado_pat = _kv_secret(os.environ.get("ADO_PAT_SECRET_URI", ""))
    openai_name = os.environ["OPENAI_NAME"]
    openai_deployment = os.environ["OPENAI_DEPLOYMENT"]
    mcp_server_url = os.environ["MCP_SERVER_URL"]
    slack_webhook = _kv_secret(os.environ.get("SLACK_WEBHOOK_SECRET_URI", ""))
    cosmos_endpoint = os.environ["COSMOS_ENDPOINT"]
    cosmos_db = os.environ["COSMOS_DB"]
    cosmos_container = os.environ["COSMOS_CONTAINER"]
    max_attempts = int(os.environ.get("MAX_ATTEMPTS_PER_PIPELINE", "3"))
    cooldown_minutes = int(os.environ.get("COOLDOWN_MINUTES", "60"))
    allowed_repos = set(json.loads(os.environ.get("ALLOWED_REPOS", "[]")))
    credential = _credential

cfg = Config()
