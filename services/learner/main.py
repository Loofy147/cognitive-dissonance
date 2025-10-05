from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn
import logging
from services.common.logging_config import configure_logging
from services.common.metrics import instrument_request
from fastapi import Request

configure_logging()
logger = logging.getLogger('learner')
app = FastAPI()
SERVICE_NAME='learner'

class UpdatePayload(BaseModel):
    proposal: dict
    contradiction: dict

@app.middleware("http")
async def add_metrics(request: Request, call_next):
    instrument_request(SERVICE_NAME, request.url.path, request.method)
    return await call_next(request)

@app.get('/health')
def health():
    return {'status': 'ok'}

@app.post('/update')
async def update(payload: UpdatePayload):
    # placeholder: compute simple loss and 'apply' update
    p = payload.proposal['predictions'][0]['p']
    cp = payload.contradiction['contradictory'][0]['p']
    # example loss: squared diff
    loss = (p - cp)**2
    logger.info({'event':'update', 'loss': loss})
    # Return a snapshot id (would be MLflow tag in real scenario)
    return {'status':'updated', 'loss': loss, 'snapshot_id': 'snap-0001'}

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)