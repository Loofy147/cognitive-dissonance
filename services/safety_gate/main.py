from fastapi import FastAPI
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import uvicorn
import logging
from services.common.logging_config import configure_logging
from services.common.metrics import instrument_request
from fastapi import Request
from services.common import config

configure_logging()
logger = logging.getLogger('safety-gate')
limiter = Limiter(key_func=get_remote_address)
app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
SERVICE_NAME='safety-gate'

class Contradiction(BaseModel):
    input_id: str
    contradictory: list
    critic_version: str
    d: float

@app.middleware("http")
@limiter.limit("100/minute")
async def add_metrics(request: Request, call_next):
    instrument_request(SERVICE_NAME, request.url.path, request.method)
    return await call_next(request)

@app.get('/health')
def health():
    return {'status': 'ok'}

@app.get('/config')
def get_config():
    """Returns non-sensitive service configuration."""
    return {
        "max_dissonance": config.MAX_DISSONANCE
    }

@app.post('/check')
async def check(c: Contradiction, request: Request):
    # Convert the Pydantic model to a dict to check for unexpected fields.
    payload = await request.json()
    expected_fields = set(Contradiction.model_fields.keys())
    received_fields = set(payload.keys())

    if not received_fields.issubset(expected_fields):
        extra_fields = received_fields - expected_fields
        logger.warning(f"Safety gate bypass attempt: unexpected fields in payload: {extra_fields}")
        # Even if the payload is otherwise valid, the presence of unexpected
        # fields could be an attempt to exploit downstream services.
        return {'allow': False, 'reason': 'unexpected_fields_in_payload'}

    # Simple safety rule: if dissonance is extremely high, block.
    if c.d > config.MAX_DISSONANCE:
        logger.warning({'event':'safety_block', 'input_id': c.input_id, 'd': c.d, 'reason': 'dissonance_too_high'})
        return {'allow': False, 'reason': 'dissonance_too_high'}

    return {'allow': True}

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)