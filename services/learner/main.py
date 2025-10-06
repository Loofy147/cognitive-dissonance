from fastapi import FastAPI, HTTPException
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
    features: dict

@app.middleware("http")
async def add_metrics(request: Request, call_next):
    instrument_request(SERVICE_NAME, request.url.path, request.method)
    return await call_next(request)

@app.get('/health')
def health():
    return {'status': 'ok'}

@app.post('/update')
async def update(payload: UpdatePayload):
    try:
        # Safely access nested data
        p = payload.proposal.get('predictions', [])[0]['p']
        cp = payload.contradiction.get('contradictory', [])[0]['p']
        input_id = payload.proposal.get('input_id')
    except (IndexError, KeyError) as e:
        logger.error(f"Malformed payload received. Missing key or empty list. Details: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Malformed payload. Missing key or empty list. Details: {e}"
        )

    # example loss: squared diff, which is the squared dissonance
    loss = (p - cp)**2

    # In a real scenario, this is where you would use the features and the loss
    # to update the model weights (e.g., via backpropagation).
    # For now, we just log it.
    logger.info({
        'event': 'update',
        'input_id': input_id,
        'loss': loss,
        'features': payload.features
    })

    # Return a snapshot id (would be MLflow run ID or model version in a real scenario)
    return {'status':'updated', 'loss': loss, 'snapshot_id': 'snap-0001'}

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)