from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import uvicorn
import mlflow
import numpy as np
import pandas as pd
import logging
import sys
import math
import time
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
    Manages the application's lifespan. The model is loaded from the MLflow
    Model Registry on startup, with a retry mechanism.
    """
    mlflow.set_tracking_uri(config.MLFLOW_TRACKING_URI)
    model_uri = f"models:/{config.CRITIC_MODEL_NAME}@production"
    logger.info(f"Attempting to load model from MLflow: {model_uri}")

    model = None
    for attempt in range(5): # Retry up to 5 times
        try:
            model = mlflow.pyfunc.load_model(model_uri)
            app.state.model = model
            app.state.model_version = model.metadata.run_id
            logger.info(f"Model loaded successfully on attempt {attempt + 1}. Version: {app.state.model_version}")
            break
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1} failed to load model: {e}. Retrying in 5 seconds...")
            time.sleep(5)

    if model is None:
        logger.critical("Failed to load model after multiple attempts. Service cannot start.")
        sys.exit(1)

    yield

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
def health(request: Request):
    if hasattr(request.app.state, 'model') and request.app.state.model is not None:
        return {'status': 'ok'}
    else:
        raise HTTPException(status_code=503, detail="Service is unhealthy: Model not loaded.")

@app.get('/config')
def get_config(request: Request):
    """Returns non-sensitive service configuration."""
    return {
        "model_name": config.CRITIC_MODEL_NAME,
        "model_version": getattr(request.app.state, 'model_version', 'N/A'),
        "mlflow_tracking_uri": config.MLFLOW_TRACKING_URI,
    }

@app.post('/contradict')
async def contradict(payload: ContradictPayload, request: Request):
    p0 = payload.predictions[0]['p']
    model = request.app.state.model
    model_version = request.app.state.model_version

    try:
        ordered_feature_names = ['f1', 'f2']
        feature_values = []
        for k in ordered_feature_names:
            value = payload.features.get(k)
            if value is None: raise KeyError(f"Missing feature: {k}")
            if not isinstance(value, (int, float)) or not math.isfinite(value):
                raise HTTPException(status_code=422, detail=f"Invalid value for feature '{k}'.")
            feature_values.append(value)

        features_array = np.array(feature_values).reshape(1, -1)

        input_df = pd.DataFrame(features_array, columns=ordered_feature_names)

        critic_probabilities = model.predict(input_df)
        cp0 = float(critic_probabilities[0])
    except KeyError as e:
        logger.error(f"Missing feature in payload: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Critic prediction failed: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

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
