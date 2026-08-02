import base64, requests, logging
from config import cfg

class AdoClient:
    def __init__(self):
        token = base64.b64encode(f":{cfg.ado_pat}".encode()).decode()
        self.headers = {"Authorization": f"Basic {token}", "Content-Type": "application/json"}
        self.base = f"https://dev.azure.com/{cfg.ado_org}"

    def _get(self, project, path, params=None):
        r = requests.get(f"{self.base}/{project}/_apis{path}",
                         headers=self.headers, params=params or {"api-version": "7.1"})
        r.raise_for_status()
        return r.json()

    def get_build(self, project, build_id):
        return self._get(project, f"/build/builds/{build_id}")

    def get_timeline(self, project, build_id):
        return self._get(project, f"/build/builds/{build_id}/timeline")

    def get_logs(self, project, build_id):
        logs = self._get(project, f"/build/builds/{build_id}/logs")
        out = []
        for log in logs.get("value", [])[:5]:  # limit to first 5 logs
            url = log["url"]
            r = requests.get(url, headers=self.headers, params={"api-version": "7.1"})
            out.append({"id": log["id"], "content": r.text[:8000]})
        return out

    def get_repo(self, project, repo_id, repo_type):
        if repo_type == "tfsgit":
            return self._get(project, f"/git/repositories/{repo_id}")
        return {}

    def create_branch_and_pr(self, project, repo_id, base_branch, new_branch, file_path, new_content, commit_msg, pr_title, pr_body):
        refs = self._get(project, f"/git/repositories/{repo_id}/refs/heads/{base_branch}")
        object_id = refs["value"][0]["objectId"]

        requests.post(
            f"{self.base}/{project}/_apis/git/repositories/{repo_id}/refs?api-version=7.1",
            headers=self.headers,
            json={"name": f"refs/heads/{new_branch}", "oldObjectId": "0000000000000000000000000000000000000000", "newObjectId": object_id},
        ).raise_for_status()

        item = self._get(project, f"/git/repositories/{repo_id}/items?path={file_path}&versionDescriptor.version={new_branch}&versionDescriptor.versionType=branch&includeContent=true")

        old_obj_id = item.get("commitId")
        push_body = {
            "refUpdates": [{"name": f"refs/heads/{new_branch}", "oldObjectId": old_obj_id or object_id}],
            "commits": [{
                "comment": commit_msg,
                "changes": [{
                    "changeType": "edit",
                    "item": {"path": file_path},
                    "newContent": {"content": new_content, "contentType": "rawtext"},
                }],
            }],
        }
        requests.post(f"{self.base}/{project}/_apis/git/repositories/{repo_id}/pushes?api-version=7.1",
                      headers=self.headers, json=push_body).raise_for_status()

        pr = requests.post(
            f"{self.base}/{project}/_apis/git/repositories/{repo_id}/pullrequests?api-version=7.1",
            headers=self.headers,
            json={
                "sourceRefName": f"refs/heads/{new_branch}",
                "targetRefName": f"refs/heads/{base_branch}",
                "title": pr_title,
                "description": pr_body,
            },
        )
        pr.raise_for_status()
        return pr.json()["webUrl"]
