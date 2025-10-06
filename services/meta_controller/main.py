from fastapi import FastAPI
import uvicorn
import logging
import json
import os
from services.common.logging_config import configure_logging
from services.common.metrics import instrument_request
from fastapi import Request
from services.common import config

configure_logging()
logger = logging.getLogger('meta-controller')
app = FastAPI()
SERVICE_NAME='meta-controller'

def _load_policy():
    """Loads policy from JSON file, or returns default if not found."""
    if os.path.exists(config.POLICY_FILE_PATH):
        try:
            with open(config.POLICY_FILE_PATH, 'r') as f:
                logger.info(f"Loading policy from {config.POLICY_FILE_PATH}")
                return json.load(f)
        except (IOError, json.JSONDecodeError) as e:
            logger.error(f"Error reading policy file: {e}, using default policy.")

    logger.info("Policy file not found, using default policy.")
    return {
        'D_target': config.D_TARGET,
        'lambda_max': config.LAMBDA_MAX,
        'KL_eps': config.KL_EPS,
        'd_budget_per_hour': config.D_BUDGET_PER_HOUR
    }

def _save_policy(policy_data: dict):
    """Saves policy to JSON file."""
    try:
        with open(config.POLICY_FILE_PATH, 'w') as f:
            json.dump(policy_data, f, indent=4)
            logger.info(f"Policy saved to {config.POLICY_FILE_PATH}")
    except IOError as e:
        logger.error(f"Could not write policy to file: {e}")

# Load initial policy
policy = _load_policy()

@app.middleware("http")
async def add_metrics(request: Request, call_next):
    instrument_request(SERVICE_NAME, request.url.path, request.method)
    return await call_next(request)

@app.get('/health')
def health():
    return {'status':'ok'}

@app.get('/policy')
async def get_policy():
    return policy

@app.post('/policy')
async def set_policy(p: dict):
    policy.update(p)
    _save_policy(policy)
    logger.info({'event':'policy_update', 'policy': policy})
    return {'status':'ok', 'policy': policy}

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)