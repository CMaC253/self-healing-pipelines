from datetime import datetime, timedelta, timezone
from azure.cosmos import CosmosClient
from config import cfg

_client = CosmosClient(cfg.cosmos_endpoint, credential=cfg.credential)
_container = _client.get_database_client(cfg.cosmos_db).get_container_client(cfg.cosmos_container)

def _now() -> datetime:
    return datetime.now(timezone.utc)

def can_attempt(pipeline_id: str, repo: str) -> tuple[bool, str]:
    if cfg.allowed_repos and repo not in cfg.allowed_repos:
        return False, f"Repo '{repo}' not in allowlist"

    items = list(_container.query_items(
        query="SELECT * FROM attempts a WHERE a.pipelineId=@p ORDER BY a.timestamp DESC",
        parameters=[{"name": "@p", "value": pipeline_id}],
        enable_cross_partition_query=True,
    ))

    if len(items) >= cfg.max_attempts:
        return False, f"Max attempts ({cfg.max_attempts}) reached for pipeline {pipeline_id}"

    if items:
        last = datetime.fromisoformat(items[0]["timestamp"])
        if _now() - last < timedelta(minutes=cfg.cooldown_minutes):
            return False, f"Cooldown active ({cfg.cooldown_minutes} min)"

    return True, "OK"

def record_attempt(pipeline_id: str, repo: str, build_id: int,
                   root_cause: str, pr_url: str | None, status: str):
    _container.create_item({
        "id": f"{pipeline_id}-{build_id}-{int(_now().timestamp())}",
        "pipelineId": pipeline_id,
        "repo": repo,
        "buildId": build_id,
        "rootCause": root_cause,
        "prUrl": pr_url,
        "status": status,
        "timestamp": _now().isoformat(),
    })
