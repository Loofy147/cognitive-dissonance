from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
import uvicorn
import pickle
import numpy as np
import logging
import sys
from services.common.metrics import instrument_request
from services.common.logging_config import configure_logging
from services.common import config

# Configure logging
configure_logging()
logger = logging.getLogger('proposer')
app = FastAPI()
SERVICE_NAME = 'proposer'

# Load the model at startup, and fail fast if it's not available.
try:
    with open(config.PROPOSER_MODEL_PATH, 'rb') as f:
        model = pickle.load(f)
    logger.info(f"Model loaded successfully from {config.PROPOSER_MODEL_PATH}")
    model_version = 'proposer-v2-sklearn'
except (FileNotFoundError, IOError, pickle.UnpicklingError) as e:
    logger.critical(f"Failed to load model: {e}. Service cannot start.")
    sys.exit(1) # Fail fast

class Input(BaseModel):
    input_id: str
    features: dict

@app.middleware("http")
async def add_metrics(request: Request, call_next):
    instrument_request(SERVICE_NAME, request.url.path, request.method)
    return await call_next(request)

@app.get('/health')
def health():
    # If the model failed to load, the service would have already exited.
    # So, if we reach here, the service is healthy.
    return {'status': 'ok'}

@app.get('/config')
def get_config():
    """Returns non-sensitive service configuration."""
    return {
        "model_path": config.PROPOSER_MODEL_PATH,
        "model_version": model_version
    }

@app.post('/predict')
async def predict(item: Input):
    # The fail-fast on startup removes the need to check if the model is None.
    try:
        # Enforce a canonical feature order to prevent incorrect predictions.
        ordered_feature_names = ['f1', 'f2']
        feature_values = [item.features[k] for k in ordered_feature_names]
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
    except KeyError as e:
        logger.error(f"Missing feature in payload: {e}")
        raise HTTPException(status_code=400, detail=f"Missing required feature: {e}")
    except Exception as e:
        logger.error(f"Prediction failed: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error during prediction: {e}")

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)