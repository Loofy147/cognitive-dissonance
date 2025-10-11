from fastapi import FastAPI, Request
import uvicorn
import httpx
import uuid
import logging
import asyncio
import numpy as np
from services.common.logging_config import configure_logging
from services.common.metrics import instrument_request, EVALUATION_LOOP_TIMEOUTS_TOTAL
from services.common import config
from contextlib import asynccontextmanager
import datetime

configure_logging()
logger = logging.getLogger('evaluator')
SERVICE_NAME = 'evaluator'

# This function contains the core orchestration logic
async def _run_orchestration_cycle(app: FastAPI):
    input_id = str(uuid.uuid4())
    features = {'f1': round(np.random.uniform(0, 2), 2), 'f2': round(np.random.uniform(0, 2), 2)}

    client = app.state.http_client
    r = await client.post(config.PROPOSER_URL, json={'input_id': input_id, 'features': features})
    proposal = r.json()
    logger.info({'stage': 'proposed', 'proposal': proposal})

    critic_payload = {**proposal, 'features': features}
    c = await client.post(config.CRITIC_URL, json=critic_payload)
    contradiction = c.json()
    logger.info({'stage': 'contradicted', 'contradiction': contradiction})

    s = await client.post(config.SAFETY_URL, json=contradiction)
    safety = s.json()
    logger.info({'stage': 'safety', 'result': safety})
    if not safety.get('allow', False):
        return {'status': 'blocked_by_safety', 'reason': safety.get('reason')}

    learner_payload = {'proposal': proposal, 'contradiction': contradiction, 'features': features}
    u = await client.post(config.LEARNER_URL, json=learner_payload)
    updated = u.json()
    logger.info({'stage': 'learner', 'updated': updated})

    return {'status': 'completed', 'input_id': input_id}

async def evaluation_loop(app: FastAPI):
    """The main evaluation loop running in the background."""
    while True:
        try:
            await asyncio.wait_for(_run_orchestration_cycle(app), timeout=config.EVALUATOR_LOOP_TIMEOUT_SECONDS)
            app.state.last_run_timestamp = datetime.datetime.now(datetime.UTC).isoformat()
        except asyncio.TimeoutError:
            logger.warning(f'run_once call timed out after {config.EVALUATOR_LOOP_TIMEOUT_SECONDS} seconds.')
            EVALUATION_LOOP_TIMEOUTS_TOTAL.labels(service=SERVICE_NAME).inc()
        except asyncio.CancelledError:
            logger.info("Evaluation loop cancelled.")
            break
        except Exception as e:
            logger.exception('loop error')
        await asyncio.sleep(2.0)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application state and background tasks."""
    app.state.last_run_timestamp = None
    app.state.http_client = httpx.AsyncClient(timeout=10.0)
    loop = asyncio.get_event_loop()
    task = loop.create_task(evaluation_loop(app))
    yield
    task.cancel()
    await app.state.http_client.aclose()
    try:
        await task
    except asyncio.CancelledError:
        logger.info("Evaluation loop task successfully cancelled.")

app = FastAPI(lifespan=lifespan)

@app.middleware("http")
async def add_metrics(request: Request, call_next):
    instrument_request(SERVICE_NAME, request.url.path, request.method)
    return await call_next(request)

@app.get('/health')
def health(request: Request):
    return {
        'status': 'ok',
        'last_run_timestamp': request.app.state.last_run_timestamp
    }

@app.get('/config')
def get_config():
    """Returns non-sensitive service configuration."""
    return {
        "proposer_url": config.PROPOSER_URL,
        "critic_url": config.CRITIC_URL,
        "learner_url": config.LEARNER_URL,
        "safety_gate_url": config.SAFETY_URL,
        "loop_timeout_seconds": config.EVALUATOR_LOOP_TIMEOUT_SECONDS
    }

@app.post('/run_once')
async def run_once_endpoint(request: Request):
    """Endpoint to trigger a single orchestration cycle for testing."""
    return await _run_orchestration_cycle(request.app)

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)