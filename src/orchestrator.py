import logging, hashlib
from config import cfg
from guardrails import can_attempt, record_attempt
from ado_client import AdoClient
from ai_agent import SelfHealingAgent
from notifications import notify

def run_self_healing(build_id: int, project: str) -> dict:
    ado = AdoClient()

    build = ado.get_build(project, build_id)
    repo = build.get("repository", {})
    repo_id = repo.get("id")
    repo_name = repo.get("name", "unknown")
    repo_type = repo.get("type")
    pipeline_id = str(build.get("definition", {}).get("id", build_id))
    full_repo = f"{cfg.ado_org}/{repo_name}"

    ok, reason = can_attempt(pipeline_id, full_repo)
    if not ok:
        logging.warning(f"Skipping: {reason}")
        return {"skipped": True, "reason": reason}

    timeline = ado.get_timeline(project, build_id)
    failed_records = [r for r in timeline.get("records", []) if r.get("result") == "failed"]
    logs = ado.get_logs(project, build_id)

    failure_context = {
        "build_id": build_id,
        "project": project,
        "repo": repo_name,
        "repo_id": repo_id,
        "source_branch": build.get("sourceBranch"),
        "source_version": build.get("sourceVersion"),
        "definition": build.get("definition", {}).get("name"),
        "failed_tasks": [
            {"name": r.get("name"), "type": r.get("type"),
             "issue": r.get("issueTypes"), "log": r.get("log", {}).get("url")}
            for r in failed_records
        ],
        "logs": logs,
    }

    agent = SelfHealingAgent()
    result = agent.run(build_id=build_id, project=project, failure_context=failure_context)

    pr_url = result.get("pr_url")
    root_cause = result.get("root_cause", "unknown")
    status = "pr_created" if pr_url else "diagnosed_only"

    record_attempt(pipeline_id, full_repo, build_id, root_cause, pr_url, status)
    notify(
        title=f" Self-Healing: {build.get('definition', {}).get('name')} build #{build_id}",
        root_cause=root_cause,
        category=result.get("category", "UNKNOWN"),
        fix=result.get("fix_applied", ""),
        pr_url=pr_url,
        summary=result.get("summary", ""),
        repo=repo_name,
    )

    return result
