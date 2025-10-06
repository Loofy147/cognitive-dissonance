from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn
import logging
from services.common.logging_config import configure_logging
from services.common.metrics import instrument_request
from fastapi import Request
from services.common import config

configure_logging()
logger = logging.getLogger('safety-gate')
app = FastAPI()
SERVICE_NAME='safety-gate'

class Contradiction(BaseModel):
    input_id: str
    contradictory: list
    critic_version: str
    d: float

@app.middleware("http")
async def add_metrics(request: Request, call_next):
    instrument_request(SERVICE_NAME, request.url.path, request.method)
    return await call_next(request)

@app.get('/health')
def health():
    return {'status': 'ok'}

@app.post('/check')
async def check(c: Contradiction):
    # simple safety rule: if dissonance extremely high, block
    if c.d > config.MAX_DISSONANCE:
        logger.warning({'event':'safety_block', 'input_id': c.input_id, 'd': c.d})
        return {'allow': False, 'reason': 'dissonance_too_high'}
    return {'allow': True}

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)