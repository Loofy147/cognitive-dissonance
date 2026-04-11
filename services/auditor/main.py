import asyncio
import datetime
import logging
import os
from typing import Optional

import httpx
import mlflow
import uvicorn
from fastapi import FastAPI, Request

from services.common import config
from services.common.logging_config import configure_logging

configure_logging()
logger = logging.getLogger("auditor")

app = FastAPI()


@app.on_event("startup")
async def startup_event():
    app.state.http_client = httpx.AsyncClient()


@app.on_event("shutdown")
async def shutdown_event():
    await app.state.http_client.aclose()


async def _check_mlflow_connectivity():
    try:
        mlflow.set_tracking_uri(config.MLFLOW_TRACKING_URI)
        mlflow.search_experiments()
    except Exception as e:
        return {
            "id": "MLFLOW_CONNECTIVITY_FAILED",
            "detail": f"Could not connect to MLflow at {config.MLFLOW_TRACKING_URI}: {e}",
        }
    return None


async def _check_evaluator_liveness(client):
    try:
        url = config.HEALTH_CHECK_URLS["evaluator"]
        response = await client.get(url, timeout=5.0)
        response.raise_for_status()
        health_data = response.json()
        last_run = health_data.get("last_run_timestamp")
        if not last_run:
            return {
                "id": "EVALUATOR_NO_RUN_HISTORY",
                "detail": "Evaluator has not yet completed a run.",
            }

        # Check if last run was within the last 5 minutes
        last_run_dt = datetime.datetime.fromisoformat(last_run)
        # Handle offset-naive vs offset-aware
        if last_run_dt.tzinfo is None:
            now = datetime.datetime.now()
        else:
            now = datetime.datetime.now(datetime.timezone.utc)

        time_since_last_run = now - last_run_dt
        if time_since_last_run.total_seconds() > 300:
            msg = (
                f"Evaluator loop seems stuck. "
                f"Last run was {time_since_last_run.total_seconds():.0f}s ago."
            )
            return {
                "id": "EVALUATOR_STUCK",
                "detail": msg,
            }
    except Exception as e:
        return {
            "id": "EVALUATOR_LIVENESS_CHECK_FAILED",
            "detail": f"Could not check evaluator liveness: {e}",
        }
    return None


async def _check_service_health(client, service_name, url):
    try:
        response = await client.get(url, timeout=5.0)
        response.raise_for_status()
        health_status = response.json()
        if health_status.get("status") != "ok":
            return {
                "id": "SERVICE_UNHEALTHY",
                "detail": f"Service '{service_name}' reported unhealthy status.",
            }
    except Exception as e:
        return {
            "id": "SERVICE_HEALTH_CHECK_FAILED",
            "detail": f"Health check failed for '{service_name}': {e}",
        }
    return None


async def _check_service_config(client, service_name, url):
    try:
        response = await client.get(url, timeout=5.0)
        response.raise_for_status()
        service_config = response.json()
        if service_name != "learner" and not service_config:
            return {
                "id": "CONFIG_EMPTY",
                "detail": f"Service '{service_name}' returned empty config.",
            }
    except Exception as e:
        return {
            "id": "CONFIG_CHECK_FAILED",
            "detail": f"Config check failed for '{service_name}': {e}",
        }
    return None


async def _run_system_audit(http_client: httpx.AsyncClient):
    findings = []

    # Check 1: MLflow Connectivity
    mlflow_finding = await _check_mlflow_connectivity()
    if mlflow_finding:
        findings.append(mlflow_finding)

    # Check 2 & 3: Live health and configuration checks
    health_tasks = [
        _check_service_health(http_client, name, url)
        for name, url in config.HEALTH_CHECK_URLS.items()
    ]
    config_tasks = [
        _check_service_config(http_client, name, url)
        for name, url in config.CONFIG_URLS.items()
    ]
    evaluator_liveness_task = _check_evaluator_liveness(http_client)

    tasks = health_tasks + config_tasks + [evaluator_liveness_task]
    results = await asyncio.gather(*tasks)

    for result in results:
        if result:
            findings.append(result)

    return findings


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/audit")
async def run_audit(request: Request):
    http_client = request.app.state.http_client
    findings = await _run_system_audit(http_client)
    return {"status": "completed", "findings": findings}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
