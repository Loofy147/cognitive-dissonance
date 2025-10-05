from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn
import logging
from services.common.logging_config import configure_logging
from services.common.metrics import instrument_request, set_d_value
from fastapi import Request

configure_logging()
logger = logging.getLogger('critic')
app=FastAPI()
SERVICE_NAME='critic'

class Proposal(BaseModel):
    input_id: str
    predictions: list
    model_version: str

@app.middleware("http")
async def add_metrics(request: Request, call_next):
    instrument_request(SERVICE_NAME, request.url.path, request.method)
    return await call_next(request)

@app.get('/health')
def health():
    return {'status': 'ok'}

@app.post('/contradict')
async def contradict(proposal: Proposal):
    # Simple critic: invert probabilities and increase entropy slightly
    preds = proposal.predictions
    p0 = preds[0]['p']
    p1 = preds[1]['p']
    # critic creates a 'challenging' distribution
    cp0 = min(0.99, 1.0 - p0 + 0.05)
    cp1 = 1.0 - cp0
    # compute a toy dissonance metric (absolute diff)
    d = abs(p0 - cp0)
    set_d_value(SERVICE_NAME, d)
    logger.info({'event': 'contradict', 'input_id': proposal.input_id, 'd': d})
    return {'input_id': proposal.input_id, 'contradictory': [{'class':'A','p':cp0},{'class':'B','p':cp1}], 'critic_version': 'critic-v1', 'd': d}

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)