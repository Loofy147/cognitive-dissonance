from fastapi import FastAPI, BackgroundTasks
import uvicorn
import time
import httpx
import uuid
import logging
import asyncio
import numpy as np
from services.common.logging_config import configure_logging
from services.common.metrics import instrument_request
from fastapi import Request
from services.common import config

configure_logging()
logger = logging.getLogger('evaluator')
app = FastAPI()
SERVICE_NAME='evaluator'

@app.middleware("http")
async def add_metrics(request: Request, call_next):
    instrument_request(SERVICE_NAME, request.url.path, request.method)
    return await call_next(request)

@app.get('/health')
def health():
    return {'status': 'ok'}

@app.post('/run_once')
async def run_once():
    # One iteration orchestration for testing
    input_id = str(uuid.uuid4())
    # Use a wider range of features for better model testing
    features = {'f1': round(np.random.uniform(0, 2), 2), 'f2': round(np.random.uniform(0, 2), 2)}

    async with httpx.AsyncClient(timeout=10.0) as client:
        # 1. Proposer gets features
        r = await client.post(config.PROPOSER_URL, json={'input_id': input_id, 'features': features})
        proposal = r.json()
        logger.info({'stage':'proposed', 'proposal': proposal})

        # 2. Critic gets features and proposal
        critic_payload = {**proposal, 'features': features}
        c = await client.post(config.CRITIC_URL, json=critic_payload)
        contradiction = c.json()
        logger.info({'stage':'contradicted', 'contradiction': contradiction})

        # 3. Safety gate checks the contradiction
        s = await client.post(config.SAFETY_URL, json=contradiction)
        safety = s.json()
        logger.info({'stage':'safety', 'result': safety})
        if not safety.get('allow', False):
            return {'status':'blocked_by_safety', 'reason': safety.get('reason')}

        # 4. Learner gets the full context
        learner_payload = {'proposal': proposal, 'contradiction': contradiction, 'features': features}
        u = await client.post(config.LEARNER_URL, json=learner_payload)
        updated = u.json()
        logger.info({'stage':'learner', 'updated': updated})

    return {'status':'completed', 'input_id': input_id}

async def evaluation_loop():
    """The main evaluation loop running in the background."""
    while True:
        try:
            # Add a 30-second timeout to each orchestration cycle
            await asyncio.wait_for(run_once(), timeout=30.0)
        except asyncio.TimeoutError:
            logger.warning('run_once call timed out after 30 seconds.')
        except Exception as e:
            logger.exception('loop error')
        # Wait for 2 seconds before the next iteration
        await asyncio.sleep(2.0)

@app.post('/start_loop')
async def start_loop(background_tasks: BackgroundTasks):
    """Starts the evaluation loop as a background task."""
    background_tasks.add_task(evaluation_loop)
    logger.info("Evaluation loop started in the background.")
    return {'status': 'loop_started'}

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)