from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import uvicorn
import pickle
import numpy as np
import logging
import sys
import math
from contextlib import asynccontextmanager
from services.common.logging_config import configure_logging
from services.common.metrics import instrument_request, set_d_value
from services.common import config

# Configure logging
configure_logging()
logger = logging.getLogger('critic')
SERVICE_NAME = 'critic'

limiter = Limiter(key_func=get_remote_address)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages the application's lifespan. The model is loaded on startup.
    This prevents the service from starting if the model is not available.
    """
    try:
        with open(config.CRITIC_MODEL_PATH, 'rb') as f:
            app.state.model = pickle.load(f)
        logger.info(f"Model loaded successfully from {config.CRITIC_MODEL_PATH}")
        app.state.model_version = 'critic-v2-sklearn'
    except (FileNotFoundError, IOError, pickle.UnpicklingError) as e:
        # Unlike the proposer, the original critic had fallback logic.
        # For now, we maintain that by logging an error but not exiting.
        # A future improvement would be to make this fail-fast as well.
        logger.error(f"Failed to load model: {e}. Critic will use fallback logic.")
        app.state.model = None
        app.state.model_version = 'critic-v1-fallback'
    yield
    # Clean up resources on shutdown
    app.state.model = None
    app.state.model_version = None

app = FastAPI(lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

class ContradictPayload(BaseModel):
    input_id: str
    predictions: list
    model_version: str
    features: dict

@app.middleware("http")
@limiter.limit("100/minute")
async def add_metrics(request: Request, call_next):
    instrument_request(SERVICE_NAME, request.url.path, request.method)
    return await call_next(request)

@app.get('/health')
def health():
    # Health is okay even if model is not loaded, as it has fallback logic.
    return {'status': 'ok'}

@app.get('/config')
def get_config(request: Request):
    """Returns non-sensitive service configuration."""
    return {
        "model_path": config.CRITIC_MODEL_PATH,
        "model_version": request.app.state.model_version
    }

@app.post('/contradict')
async def contradict(payload: ContradictPayload, request: Request):
    p0 = payload.predictions[0]['p']
    # Safely access model and version from app state, providing defaults.
    model = getattr(request.app.state, 'model', None)
    model_version = getattr(request.app.state, 'model_version', 'critic-v1-fallback')

    if model is None:
        # Fallback to simple logic if model is not loaded
        cp0 = min(0.99, 1.0 - p0 + 0.05)
    else:
        try:
            ordered_feature_names = ['f1', 'f2']
            feature_values = []
            for k in ordered_feature_names:
                value = payload.features[k]
                if not isinstance(value, (int, float)) or not math.isfinite(value):
                    raise HTTPException(status_code=422, detail=f"Invalid value for feature '{k}': must be a finite number.")
                feature_values.append(value)

            features_array = np.array(feature_values).reshape(1, -1)
            critic_probabilities = model.predict_proba(features_array)[0]
            cp0 = critic_probabilities[0]
        except KeyError as e:
            logger.error(f"Missing feature in payload: {e}")
            raise HTTPException(status_code=400, detail=f"Missing required feature: {e}")
        except Exception as e:
            logger.error(f"Critic prediction failed: {e}")
            raise HTTPException(status_code=500, detail=f"Error during critic prediction: {e}")

    cp1 = 1.0 - cp0
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