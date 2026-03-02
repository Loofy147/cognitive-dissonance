from fastapi import FastAPI, Request
import uvicorn
import os
import httpx
import asyncio
import datetime
import mlflow
from contextlib import asynccontextmanager
from services.common import config

# Define a threshold for the evaluator loop.
EVALUATOR_LOOP_STUCK_THRESHOLD_SECONDS = config.EVALUATOR_LOOP_TIMEOUT_SECONDS * 1.5

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize the client on startup
    async with httpx.AsyncClient() as client:
        app.state.http_client = client
        yield

app = FastAPI(lifespan=lifespan)
SERVICE_NAME = 'auditor'

async def _check_mlflow_connectivity():
    """Checks if the MLflow tracking server is reachable."""
    try:
        mlflow.set_tracking_uri(config.MLFLOW_TRACKING_URI)
        mlflow.search_experiments()
        return None
    except Exception as e:
        return {"id": "MLFLOW_UNREACHABLE", "detail": f"Could not connect to MLflow at {config.MLFLOW_TRACKING_URI}: {e}"}

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
        if last_run_dt.tzinfo is None:
             last_run_dt = last_run_dt.replace(tzinfo=datetime.timezone.utc)

        time_since_last_run = datetime.datetime.now(datetime.timezone.utc) - last_run_dt

        if time_since_last_run.total_seconds() > EVALUATOR_LOOP_STUCK_THRESHOLD_SECONDS:
            return {
                "id": "EVALUATOR_STUCK",
                "detail": f"Evaluator loop seems stuck. Last run was {time_since_last_run.total_seconds():.0f}s ago."
            }
    except httpx.RequestError:
        return None
    except Exception as e:
        return {"id": "EVALUATOR_LIVENESS_CHECK_FAILED", "detail": f"Error checking evaluator liveness: {e}"}

    return None

async def _check_service_health(client, service_name, url):
    try:
        response = await client.get(url, timeout=5.0)
        response.raise_for_status()
        health_status = response.json()
        if health_status.get("status") != "ok":
            return {"id": "SERVICE_UNHEALTHY", "detail": f"Service '{service_name}' reported unhealthy status."}
    except Exception as e:
        return {"id": "SERVICE_HEALTH_CHECK_FAILED", "detail": f"Health check failed for '{service_name}': {e}"}
    return None

async def _check_service_config(client, service_name, url):
    try:
        response = await client.get(url, timeout=5.0)
        response.raise_for_status()
        service_config = response.json()
        if service_name != 'learner' and not service_config:
            return {"id": "CONFIG_EMPTY", "detail": f"Service '{service_name}' returned empty config."}
    except Exception as e:
        return {"id": "CONFIG_CHECK_FAILED", "detail": f"Config check failed for '{service_name}': {e}"}
    return None

async def _run_system_audit(http_client: httpx.AsyncClient):
    findings = []

    # Check 1: MLflow Connectivity
    mlflow_finding = await _check_mlflow_connectivity()
    if mlflow_finding:
        findings.append(mlflow_finding)

    # Check 2 & 3: Live health and configuration checks
    health_tasks = [_check_service_health(http_client, name, url) for name, url in config.HEALTH_CHECK_URLS.items()]
    config_tasks = [_check_service_config(http_client, name, url) for name, url in config.CONFIG_URLS.items()]
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
    http_client = request.app.state.http_client
    findings = await _run_system_audit(http_client)
    return {
        "status": "completed",
        "findings": findings
    }

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)
