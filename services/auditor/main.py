from fastapi import FastAPI, Request
import uvicorn
import os
import httpx
import asyncio
import datetime
from contextlib import asynccontextmanager
from services.common import config

# Define a threshold for the evaluator loop. If the last successful run was before
# this many seconds ago, we'll consider it stuck. This should be greater than
# the evaluator's own loop timeout to avoid false positives.
EVALUATOR_LOOP_STUCK_THRESHOLD_SECONDS = config.EVALUATOR_LOOP_TIMEOUT_SECONDS * 1.5

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize the client on startup and add it to the application state
    async with httpx.AsyncClient() as client:
        app.state.http_client = client
        yield
    # The client is automatically closed by the context manager on shutdown

app = FastAPI(lifespan=lifespan)
SERVICE_NAME = 'auditor'

async def _check_evaluator_liveness(client: httpx.AsyncClient):
    """Checks if the evaluator's main loop is running."""
    url = config.HEALTH_CHECK_URLS.get("evaluator")
    if not url:
        return {"id": "CONFIG_MISSING", "detail": "Evaluator health check URL not configured."}

    try:
        response = await client.get(url, timeout=5.0)
        response.raise_for_status()
        health_status = response.json()

        last_run_iso = health_status.get("last_run_timestamp")
        if not last_run_iso:
            return {"id": "EVALUATOR_NOT_RUN", "detail": "Evaluator has not completed a cycle yet."}

        last_run_dt = datetime.datetime.fromisoformat(last_run_iso)

        # Ensure the timestamp is timezone-aware for correct comparison
        if last_run_dt.tzinfo is None:
             last_run_dt = last_run_dt.replace(tzinfo=datetime.timezone.utc)

        time_since_last_run = datetime.datetime.now(datetime.timezone.utc) - last_run_dt

        if time_since_last_run.total_seconds() > EVALUATOR_LOOP_STUCK_THRESHOLD_SECONDS:
            return {
                "id": "EVALUATOR_STUCK",
                "detail": f"Evaluator loop seems stuck. Last run was {time_since_last_run.total_seconds():.0f}s ago (threshold: {EVALUATOR_LOOP_STUCK_THRESHOLD_SECONDS}s)."
            }
    except httpx.RequestError:
        # This failure is already covered by the generic health check, so we don't need to add a finding here.
        return None
    except Exception as e:
        return {"id": "EVALUATOR_LIVENESS_CHECK_FAILED", "detail": f"An unexpected error occurred while checking evaluator liveness: {e}"}

    return None

async def _check_service_health(client, service_name, url):
    """Checks the health of a single service, distinguishing between different failure modes."""
    try:
        response = await client.get(url, timeout=5.0)
        response.raise_for_status()

        health_status = response.json()
        # For the evaluator, the liveness check is more specific, so we only check for "ok" status here.
        if health_status.get("status") != "ok":
            return {"id": "SERVICE_UNHEALTHY", "detail": f"Service '{service_name}' reported an unhealthy status: {health_status}"}
    except httpx.HTTPStatusError as e:
        return {"id": "SERVICE_UNHEALTHY", "detail": f"Service '{service_name}' is reachable but returned a non-200 status code: {e.response.status_code}"}
    except httpx.RequestError as e:
        return {"id": "SERVICE_UNREACHABLE", "detail": f"Service '{service_name}' is unreachable at {url}. Error: {type(e).__name__}"}
    except Exception as e:
        return {"id": "SERVICE_HEALTH_CHECK_FAILED", "detail": f"An unexpected error occurred while checking service '{service_name}'. Error: {e}"}
    return None

async def _check_service_config(client, service_name, url):
    """Checks the configuration of a single service for potential issues."""
    try:
        response = await client.get(url, timeout=5.0)
        response.raise_for_status()

        service_config = response.json()
        # The learner service is expected to have an empty config for now.
        if service_name != 'learner' and not service_config:
            return {
                "id": "CONFIG_EMPTY",
                "detail": f"Service '{service_name}' returned an empty configuration."
            }
    except Exception as e:
        return {
            "id": "CONFIG_CHECK_FAILED",
            "detail": f"Failed to check configuration for service '{service_name}'. Error: {e}"
        }
    return None

async def _run_system_audit(http_client: httpx.AsyncClient):
    """
    Runs a series of checks against the system to find common issues.
    """
    findings = []

    # Check 1: Ensure critical model files exist.
    if not os.path.exists(config.PROPOSER_MODEL_PATH):
        findings.append({"id": "MODEL_FILE_MISSING", "detail": f"Proposer model file not found at {config.PROPOSER_MODEL_PATH}"})
    if not os.path.exists(config.CRITIC_MODEL_PATH):
        findings.append({"id": "MODEL_FILE_MISSING", "detail": f"Critic model file not found at {config.CRITIC_MODEL_PATH}"})

    # Check 2 & 3: Perform live health and configuration checks on all services.
    health_tasks = [_check_service_health(http_client, name, url) for name, url in config.HEALTH_CHECK_URLS.items()]
    config_tasks = [_check_service_config(http_client, name, url) for name, url in config.CONFIG_URLS.items()]

    # Check 4: Add the specific evaluator liveness check
    evaluator_liveness_task = _check_evaluator_liveness(http_client)

    tasks = health_tasks + config_tasks + [evaluator_liveness_task]
    results = await asyncio.gather(*tasks)

    for result in results:
        if result:
            findings.append(result)

    return findings

@app.get('/health')
def health():
    return {'status': 'ok'}

@app.post('/audit')
async def run_audit(request: Request):
    """
    Triggers a system audit and returns a list of findings.
    """
    http_client = request.app.state.http_client
    findings = await _run_system_audit(http_client)
    return {
        "status": "completed",
        "findings": findings
    }

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)