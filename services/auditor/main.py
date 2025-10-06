from fastapi import FastAPI
import uvicorn
import os
from services.common import config

app = FastAPI()
SERVICE_NAME = 'auditor'

def _run_system_audit():
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

    return findings

@app.get('/health')
def health():
    return {'status': 'ok'}

@app.post('/audit')
async def run_audit():
    """
    Triggers a system audit and returns a list of findings.
    """
    findings = _run_system_audit()
    return {
        "status": "completed",
        "findings": findings
    }

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)