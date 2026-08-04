import logging, json
from config import cfg
from guardrails import can_attempt, record_attempt
from ado_client import AdoClient
from ai_agent import SelfHealingAgent
from notifications import notify
from prompts.base_prompt import BASE_PROMPT
from prompts.skill_terraform import TERRAFORM_SKILL
from prompts.skill_ansible import ANSIBLE_SKILL
from prompts.skill_yaml_pipeline import YAML_PIPELINE_SKILL

def determine_skill(failure_context: dict) -> str:
    """Analyzes logs to determine which expert skill prompt to inject."""
    # Convert the whole context to a string for easy searching
    logs = json.dumps(failure_context).lower()
    
    if "terraform" in logs or "tflint" in logs or ".tf" in logs:
        logging.info("Skill Router: Terraform expertise engaged.")
        return TERRAFORM_SKILL
    elif "ansible" in logs or "playbook" in logs:
        logging.info("Skill Router: Ansible expertise engaged.")
        return ANSIBLE_SKILL
    elif "azure-pipelines.yml" in logs or "task:" in logs:
        logging.info("Skill Router: ADO YAML expertise engaged.")
        return YAML_PIPELINE_SKILL
    
    logging.info("Skill Router: No specific skill detected, using base prompt.")
    return ""

def run_self_healing(build_id: int, project: str) -> dict:
    ado = AdoClient()

    build = ado.get_build(project, build_id)
    repo = build.get("repository", {})
    repo_id = repo.get("id")
    repo_name = repo.get("name", "unknown")
    repo_type = repo.get("type")
    pipeline_id = str(build.get("definition", {}).get("id", build_id))
    full_repo = f"{cfg.ado_org}/{repo_name}"

    # 1. Check Guardrails
    ok, reason = can_attempt(pipeline_id, full_repo)
    if not ok:
        logging.warning(f"Skipping: {reason}")
        return {"skipped": True, "reason": reason}

    # 2. Gather Context
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

    # 3. Route to the correct Expert Skill
    skill_prompt = determine_skill(failure_context)
    full_system_prompt = BASE_PROMPT + "\n" + skill_prompt

    # 4. Run Agent with specialized prompt
    agent = SelfHealingAgent(system_prompt=full_system_prompt)
    result = agent.run(build_id=build_id, project=project, failure_context=failure_context)

    pr_url = result.get("pr_url")
    root_cause = result.get("root_cause", "unknown")
    status = "pr_created" if pr_url else "diagnosed_only"

    # 5. Persist + Notify
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
