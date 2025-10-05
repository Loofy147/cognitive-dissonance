from fastapi import FastAPI, Request
from pydantic import BaseModel
import uvicorn
import uuid
from services.common.metrics import instrument_request
from services.common.logging_config import configure_logging
import logging

configure_logging()
logger = logging.getLogger('proposer')
app = FastAPI()
SERVICE_NAME = 'proposer'

class Input(BaseModel):
    input_id: str
    features: dict

@app.middleware("http")
async def add_metrics(request: Request, call_next):
    instrument_request(SERVICE_NAME, request.url.path, request.method)
    return await call_next(request)

@app.get('/health')
def health():
    return {'status': 'ok'}

@app.post('/predict')
async def predict(item: Input):
    # placeholder simple model: sum of numeric features as score
    features = item.features
    score = 0.0
    for v in features.values():
        try:
            score += float(v)
        except Exception:
            pass
    # return distribution across two classes as softmax-like
    p0 = 1.0 / (1.0 + score + 1e-9)
    p1 = 1.0 - p0
    model_version = 'proposer-v1'
    logger.info({'event': 'predict', 'input_id': item.input_id, 'p0': p0, 'p1': p1})
    return {'input_id': item.input_id, 'predictions': [{'class': 'A', 'p': p0}, {'class': 'B', 'p': p1}], 'model_version': model_version}

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)