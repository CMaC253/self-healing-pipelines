import azure.functions as func
import logging, json
from orchestrator import run_self_healing

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

@app.route(route="pipeline-failed", methods=["POST"])
def pipeline_failed(req: func.HttpRequest) -> func.HttpResponse:
    try:
        body = req.get_json()
    except ValueError:
        return func.HttpResponse("Invalid JSON", status_code=400)

    resource = body.get("resource", body)
    build_id = resource.get("id") or resource.get("buildId")
    project = body.get("resourceContainers", {}).get("project", {}).get("id") \
              or resource.get("project", {}).get("name")
    status = resource.get("result") or resource.get("status")

    logging.info(f"Received hook: build={build_id}, project={project}, status={status}")

    if status not in ("failed", "canceled"):
        return func.HttpResponse("Ignored: not a failure", status_code=200)

    try:
        result = run_self_healing(build_id=build_id, project=project)
        return func.HttpResponse(json.dumps(result), status_code=200,
                                 mimetype="application/json")
    except Exception as e:
        logging.exception("Self-healing failed")
        return func.HttpResponse(str(e), status_code=500)
