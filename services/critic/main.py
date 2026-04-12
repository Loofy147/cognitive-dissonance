import logging
import math
import os
import sys
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

import mlflow
import numpy as np
import pandas as pd
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from services.common import config
from services.common.logging_config import configure_logging
from services.common.metrics import instrument_request, set_d_value
from services.common.solvers import wonderland_solver

# Configure logging
configure_logging()
logger = logging.getLogger("critic")
SERVICE_NAME = "critic"

limiter = Limiter(key_func=get_remote_address)


class CriticState:
    def __init__(self):
        self.models: Dict[str, Any] = {}
        self.model_versions: Dict[str, str] = {}

    def load_task_model(self, task_id: str):
        task_cfg = config.get_task_config(task_id)
        model_name = task_cfg["critic_model_name"]
        model_uri = f"models:/{model_name}@production"

        logger.info(f"Attempting to load model for task '{task_id}': {model_uri}")

        for attempt in range(5):
            try:
                model = mlflow.pyfunc.load_model(model_uri)
                self.models[task_id] = model
                self.model_versions[task_id] = model.metadata.run_id
                logger.info(
                    f"Model for task '{task_id}' loaded. Version: {self.model_versions[task_id]}"
                )
                return True
            except Exception as e:
                logger.warning(
                    f"Attempt {attempt + 1} failed for task '{task_id}': {e}. Retrying..."
                )
                time.sleep(5)
        return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Loads all models from the TASKS config on startup."""
    mlflow.set_tracking_uri(config.MLFLOW_TRACKING_URI)
    app.state.critic = CriticState()

    success = True
    for task_id in config.TASKS.keys():
        if not app.state.critic.load_task_model(task_id):
            logger.error(f"CRITICAL: Failed to load model for task '{task_id}'.")
            success = False

    if not success and not os.getenv("TEST_MODE"):
        logger.critical("Failed to load required models. Service cannot start.")
        sys.exit(1)

    yield
    app.state.critic = None


app = FastAPI(lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


class ContradictPayload(BaseModel):
    input_id: str
    task_id: Optional[str] = config.DEFAULT_TASK
    predictions: list
    model_version: str
    features: dict


@app.middleware("http")
@limiter.limit("100/minute")
async def add_metrics(request: Request, call_next):
    instrument_request(SERVICE_NAME, request.url.path, request.method)
    return await call_next(request)


@app.get("/health")
def health(request: Request):
    return {"status": "ok"}


@app.get("/config")
def get_config(request: Request):
    return {
        "tasks": list(config.TASKS.keys()),
        "mlflow_tracking_uri": config.MLFLOW_TRACKING_URI,
    }


@app.post("/contradict")
async def contradict(payload: ContradictPayload, request: Request):
    try:
        task_id = payload.task_id or config.DEFAULT_TASK
        task_cfg = config.get_task_config(task_id)

        model = request.app.state.critic.models.get(task_id)
        model_version = request.app.state.critic.model_versions.get(task_id)

        if model is None:
            raise HTTPException(
                status_code=404, detail=f"Model for task '{task_id}' not loaded."
            )

        p0 = payload.predictions[0]["p"]
        ordered_feature_names = task_cfg["feature_names"]

        # Handle reasoning tasks (text-based)
        if task_id == "nemotron_reasoning":
            prompt = payload.features.get("prompt")
            if not prompt:
                raise KeyError("Missing feature: prompt")

            # Critic uses the solver as a "truth" oracle to challenge the proposer
            answer = wonderland_solver(prompt)
            if answer:
                # If proposer's confidence was high, let's see if we agree
                cp0 = 0.9  # High confidence in solver result
            else:
                cp0 = 0.5  # Uncertain
            cp1 = 1.0 - cp0
        else:
            feature_values = []
            for k in ordered_feature_names:
                value = payload.features.get(k)
                if value is None:
                    raise KeyError(f"Missing feature: {k}")
                if not isinstance(value, (int, float)) or not math.isfinite(value):
                    raise HTTPException(
                        status_code=422, detail=f"Invalid value for feature '{k}'."
                    )
                feature_values.append(value)

            features_array = np.array(feature_values).reshape(1, -1)
            input_df = pd.DataFrame(features_array, columns=ordered_feature_names)

            critic_probabilities = model.predict(input_df)
            cp0 = float(critic_probabilities[0])
            cp1 = 1.0 - cp0

        d = abs(p0 - cp0)
        set_d_value(SERVICE_NAME, d)
        logger.info(
            {
                "event": "contradict",
                "task_id": task_id,
                "input_id": payload.input_id,
                "d": d,
            }
        )

        return {
            "input_id": payload.input_id,
            "task_id": task_id,
            "contradictory": [{"class": "A", "p": cp0}, {"class": "B", "p": cp1}],
            "critic_version": model_version,
            "d": d,
        }
    except KeyError as e:
        logger.error(f"Missing feature in payload: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Critic prediction failed: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
