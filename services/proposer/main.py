from fastapi import FastAPI, Request, HTTPException
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
from services.common.metrics import instrument_request
from services.common.logging_config import configure_logging
from services.common import config

# Configure logging
configure_logging()
logger = logging.getLogger('proposer')
SERVICE_NAME = 'proposer'

limiter = Limiter(key_func=get_remote_address)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages the application's lifespan. The model is loaded from the MLflow
    Model Registry on startup, with a retry mechanism to handle potential
    delays in model availability.
    """
    mlflow.set_tracking_uri(config.MLFLOW_TRACKING_URI)
    model_uri = f"models:/{config.PROPOSER_MODEL_NAME}@production"
    logger.info(f"Attempting to load model from MLflow: {model_uri}")

    model = None
    for attempt in range(5): # Retry up to 5 times
        try:
            model = mlflow.pyfunc.load_model(model_uri)
            app.state.model = model
            app.state.model_version = model.metadata.run_id
            logger.info(f"Model loaded successfully on attempt {attempt + 1}. Version: {app.state.model_version}")
            break # Exit loop on success
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

class Input(BaseModel):
    input_id: str
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
    return {
        "model_name": config.PROPOSER_MODEL_NAME,
        "model_version": getattr(request.app.state, 'model_version', 'N/A'),
        "mlflow_tracking_uri": config.MLFLOW_TRACKING_URI,
    }

@app.post('/predict')
async def predict(item: Input, request: Request):
    try:
        model = request.app.state.model
        model_version = request.app.state.model_version

        ordered_feature_names = ['f1', 'f2']
        feature_values = []
        for k in ordered_feature_names:
            value = item.features.get(k)
            if value is None: raise KeyError(f"Missing feature: {k}")
            if not isinstance(value, (int, float)) or not math.isfinite(value):
                raise HTTPException(status_code=422, detail=f"Invalid value for feature '{k}'.")
            feature_values.append(value)

        features_array = np.array(feature_values).reshape(1, -1)

        input_df = pd.DataFrame(features_array, columns=ordered_feature_names)

        probabilities = model.predict(input_df)
        p0 = float(probabilities[0])
        p1 = 1.0 - p0

        logger.info({'event': 'predict', 'input_id': item.input_id, 'p0': p0, 'p1': p1})

        return {
            'input_id': item.input_id,
            'predictions': [{'class': 'A', 'p': p0}, {'class': 'B', 'p': p1}],
            'model_version': model_version
        }
    except KeyError as e:
        logger.error(f"Missing feature in payload: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Prediction failed: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)
