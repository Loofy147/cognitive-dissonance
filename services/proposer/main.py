from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
import uvicorn
import pickle
import numpy as np
import logging
from services.common.metrics import instrument_request
from services.common.logging_config import configure_logging
from services.common import config

# Configure logging
configure_logging()
logger = logging.getLogger('proposer')
app = FastAPI()
SERVICE_NAME = 'proposer'

# Load the model at startup
try:
    with open(config.PROPOSER_MODEL_PATH, 'rb') as f:
        model = pickle.load(f)
    logger.info(f"Model loaded successfully from {config.PROPOSER_MODEL_PATH}")
    model_version = 'proposer-v2-sklearn'
except (FileNotFoundError, IOError, pickle.UnpicklingError) as e:
    logger.error(f"Failed to load model: {e}")
    model = None
    model_version = 'proposer-v1-fallback'

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
    if model is None:
        raise HTTPException(status_code=500, detail="Model not loaded")

    try:
        # Convert features dict to a numpy array, assuming ordered keys
        feature_values = [item.features[k] for k in sorted(item.features.keys())]
        features_array = np.array(feature_values).reshape(1, -1)

        # Get probability distribution
        probabilities = model.predict_proba(features_array)[0]
        p0, p1 = probabilities[0], probabilities[1]

        logger.info({'event': 'predict', 'input_id': item.input_id, 'p0': p0, 'p1': p1})

        return {
            'input_id': item.input_id,
            'predictions': [{'class': 'A', 'p': p0}, {'class': 'B', 'p': p1}],
            'model_version': model_version
        }
    except Exception as e:
        logger.error(f"Prediction failed: {e}")
        raise HTTPException(status_code=400, detail=f"Error processing features: {e}")

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)