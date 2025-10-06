from fastapi import FastAPI
import uvicorn
import os
import httpx
import asyncio
from services.common import config

app = FastAPI()
SERVICE_NAME = 'auditor'

async def _check_service_health(client, service_name, url):
    """Checks the health of a single service, distinguishing between different failure modes."""
    try:
        response = await client.get(url, timeout=5.0)
        response.raise_for_status()

        health_status = response.json()
        if health_status.get("status") != "ok":
            return {
                "id": "SERVICE_UNHEALTHY",
                "detail": f"Service '{service_name}' reported an unhealthy status: {health_status}"
            }
    except httpx.HTTPStatusError as e:
        return {
            "id": "SERVICE_UNHEALTHY",
            "detail": f"Service '{service_name}' is reachable but returned a non-200 status code: {e.response.status_code}"
        }
    except httpx.RequestError as e:
        return {
            "id": "SERVICE_UNREACHABLE",
            "detail": f"Service '{service_name}' is unreachable at {url}. Error: {type(e).__name__}"
        }
    except Exception as e:
        return {
            "id": "SERVICE_HEALTH_CHECK_FAILED",
            "detail": f"An unexpected error occurred while checking service '{service_name}'. Error: {e}"
        }
    return None

async def _run_system_audit():
    """
    Runs a series of checks against the system to find common issues.
    """
    findings = []

    # Check 1: Ensure critical model files exist.
    if not os.path.exists(config.PROPOSER_MODEL_PATH):
        findings.append({
            "id": "MODEL_FILE_MISSING",
            "detail": f"Proposer model file not found at {config.PROPOSER_MODEL_PATH}"
        })

    if not os.path.exists(config.CRITIC_MODEL_PATH):
        findings.append({
            "id": "MODEL_FILE_MISSING",
            "detail": f"Critic model file not found at {config.CRITIC_MODEL_PATH}"
        })

    # Check 2: Perform live health checks on all services.
    async with httpx.AsyncClient() as client:
        tasks = []
        for service_name, url in config.HEALTH_CHECK_URLS.items():
            tasks.append(_check_service_health(client, service_name, url))

        health_check_results = await asyncio.gather(*tasks)

        for result in health_check_results:
            if result:
                findings.append(result)

    return findings

@app.get('/health')
def health():
    return {'status': 'ok'}

@app.post('/audit')
async def run_audit():
    """
    Triggers a system audit and returns a list of findings.
    """
    findings = await _run_system_audit()
    return {
        "status": "completed",
        "findings": findings
    }

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)