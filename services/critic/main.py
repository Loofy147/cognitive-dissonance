from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
import uvicorn
import pickle
import numpy as np
import logging
from services.common.logging_config import configure_logging
from services.common.metrics import instrument_request, set_d_value
from services.common import config

# Configure logging
configure_logging()
logger = logging.getLogger('critic')
app = FastAPI()
SERVICE_NAME = 'critic'

# Load the model at startup
try:
    with open(config.CRITIC_MODEL_PATH, 'rb') as f:
        model = pickle.load(f)
    logger.info(f"Model loaded successfully from {config.CRITIC_MODEL_PATH}")
    model_version = 'critic-v2-sklearn'
except (FileNotFoundError, IOError, pickle.UnpicklingError) as e:
    logger.error(f"Failed to load model: {e}")
    model = None
    model_version = 'critic-v1-fallback'

class ContradictPayload(BaseModel):
    input_id: str
    predictions: list
    model_version: str
    features: dict

@app.middleware("http")
async def add_metrics(request: Request, call_next):
    instrument_request(SERVICE_NAME, request.url.path, request.method)
    return await call_next(request)

@app.get('/health')
def health():
    return {'status': 'ok'}

@app.post('/contradict')
async def contradict(payload: ContradictPayload):
    # Original proposer's prediction
    p0 = payload.predictions[0]['p']

    # Generate critic's prediction
    if model is None:
        # Fallback to simple logic if model is not loaded
        cp0 = min(0.99, 1.0 - p0 + 0.05)
    else:
        try:
            # The model was trained on features in a specific order. We must enforce that order.
            ordered_feature_names = ['f1', 'f2']
            feature_values = [payload.features[k] for k in ordered_feature_names]
            features_array = np.array(feature_values).reshape(1, -1)

            # Get critic's probability distribution
            critic_probabilities = model.predict_proba(features_array)[0]
            cp0 = critic_probabilities[0]
        except KeyError as e:
            logger.error(f"Missing feature in payload: {e}")
            raise HTTPException(status_code=400, detail=f"Missing required feature: {e}")
        except Exception as e:
            logger.error(f"Critic prediction failed: {e}")
            raise HTTPException(status_code=500, detail=f"Error during critic prediction: {e}")

    cp1 = 1.0 - cp0

    # Compute dissonance metric (absolute diff between proposer and critic)
    d = abs(p0 - cp0)
    set_d_value(SERVICE_NAME, d)
    logger.info({'event': 'contradict', 'input_id': payload.input_id, 'd': d})

    return {
        'input_id': payload.input_id,
        'contradictory': [{'class':'A','p':cp0},{'class':'B', 'p':cp1}],
        'critic_version': model_version,
        'd': d
    }

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)