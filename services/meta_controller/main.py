from fastapi import FastAPI
import uvicorn
import logging
from services.common.logging_config import configure_logging
from services.common.metrics import instrument_request
from fastapi import Request

configure_logging()
logger = logging.getLogger('meta-controller')
app = FastAPI()
SERVICE_NAME='meta-controller'

# Simple in-memory policy store for POC
policy = {
    'D_target': 0.12,
    'lambda_max': 0.05,
    'KL_eps': 0.02,
    'd_budget_per_hour': 100
}

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
    logger.info({'event':'policy_update', 'policy': policy})
    return {'status':'ok', 'policy': policy}

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)