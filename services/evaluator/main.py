from fastapi import FastAPI
import uvicorn
import time
import httpx
import uuid
import logging
from services.common.logging_config import configure_logging
from services.common.metrics import instrument_request
from fastapi import Request

configure_logging()
logger = logging.getLogger('evaluator')
app = FastAPI()
SERVICE_NAME='evaluator'

PROPOSER_URL = 'http://proposer:8000/predict'
CRITIC_URL = 'http://critic:8000/contradict'
LEARNER_URL = 'http://learner:8000/update'
SAFETY_URL = 'http://safety-gate:8000/check'

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
    features = {'f1': 1.2, 'f2': 0.5}
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.post(PROPOSER_URL, json={'input_id': input_id, 'features': features})
        proposal = r.json()
        logger.info({'stage':'proposed', 'proposal': proposal})
        c = await client.post(CRITIC_URL, json=proposal)
        contradiction = c.json()
        logger.info({'stage':'contradicted', 'contradiction': contradiction})
        # safety check
        s = await client.post(SAFETY_URL, json=contradiction)
        safety = s.json()
        logger.info({'stage':'safety', 'result': safety})
        if not safety.get('allow', False):
            return {'status':'blocked_by_safety', 'reason': safety.get('reason')}
        # send to learner
        u = await client.post(LEARNER_URL, json={'proposal': proposal, 'contradiction': contradiction})
        updated = u.json()
        logger.info({'stage':'learner', 'updated': updated})
    return {'status':'completed', 'input_id': input_id}

@app.post('/start_loop')
async def start_loop():
    # starts a background loop (naive)
    import asyncio
    async def loop():
        while True:
            try:
                await app.post('/run_once')
            except Exception as e:
                logger.exception('loop error')
            await asyncio.sleep(2.0)
    import threading
    t = threading.Thread(target=lambda: asyncio.run(loop()), daemon=True)
    t.start()
    return {'status':'loop_started'}

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)