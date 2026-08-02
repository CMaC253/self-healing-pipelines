import requests, logging
from config import cfg

def _build_slack_payload(title, root_cause, category, fix, pr_url, summary, repo):
    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": title}},
        {"type": "section", "fields": [
            {"type": "mrkdwn", "text": f"*Repo:*\n{repo}"},
            {"type": "mrkdwn", "text": f"*Category:*\n{category}"},
        ]},
        {"type": "section", "text": {"type": "mrkdwn", "text": f"*Root cause:*\n{root_cause}"}},
        {"type": "section", "text": {"type": "mrkdwn", "text": f"*Fix applied:*\n{fix}"}},
        {"type": "section", "text": {"type": "mrkdwn", "text": f"*Summary:*\n{summary}"}},
    ]
    if pr_url:
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": f":rocket: *PR:* <{pr_url}|Open pull request>"}})
    return {"blocks": blocks}

def _build_teams_payload(title, root_cause, category, fix, pr_url, summary, repo):
    facts = [
        {"name": "Repo", "value": repo},
        {"name": "Category", "value": category},
        {"name": "Root cause", "value": root_cause},
        {"name": "Fix applied", "value": fix},
    ]
    card = {
        "@type": "MessageCard",
        "@context": "http://schema.org/extensions",
        "themeColor": "0078D7",
        "summary": title,
        "title": title,
        "sections": [{"facts": facts, "text": summary}],
    }
    if pr_url:
        card["potentialAction"] = [{
            "@type": "OpenUri",
            "name": "View Pull Request",
            "targets": [{"os": "default", "uri": pr_url}],
        }]
    return card

def notify(**kwargs):
    if not cfg.slack_webhook:
        logging.warning("No webhook configured")
        return
    if "webhook.office.com" in cfg.slack_webhook:
        payload = _build_teams_payload(**kwargs)
    else:
        payload = _build_slack_payload(**kwargs)
    try:
        r = requests.post(cfg.slack_webhook, json=payload, timeout=10)
        r.raise_for_status()
    except Exception as e:
        logging.error(f"Notification failed: {e}")
