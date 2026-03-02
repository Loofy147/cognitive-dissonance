import json
import logging
import os
from contextlib import asynccontextmanager
from typing import Optional

import mlflow
import psycopg2
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from services.common import config
from services.common.logging_config import configure_logging
from services.common.metrics import instrument_request

configure_logging()
logger = logging.getLogger("learner")
SERVICE_NAME = "learner"

limiter = Limiter(key_func=get_remote_address)


def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "postgres"),
        database=os.getenv("POSTGRES_DB", "cd_meta"),
        user=os.getenv("POSTGRES_USER", "cd_user"),
        password=os.getenv("POSTGRES_PASSWORD", "cd_pass"),
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    On startup, configure the MLflow tracking URI and ensure the experiment exists.
    Also ensure the database table for dissonant samples exists.
    """
    try:
        mlflow.set_tracking_uri(config.MLFLOW_TRACKING_URI)
        mlflow.set_experiment("dissonance_learning")
        logger.info(f"MLflow tracking URI set to {config.MLFLOW_TRACKING_URI}")
        logger.info("MLflow experiment set to 'dissonance_learning'")

        # Initialize DB table
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS dissonant_samples (
                id SERIAL PRIMARY KEY,
                task_id TEXT,
                input_id TEXT,
                features JSONB,
                proposal JSONB,
                contradiction JSONB,
                loss FLOAT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        cur.close()
        conn.close()
        logger.info("Database table 'dissonant_samples' initialized.")

    except Exception as e:
        logger.error(f"Failed to configure MLflow or Database on startup: {e}")
    yield


app = FastAPI(lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


class UpdatePayload(BaseModel):
    proposal: dict
    contradiction: dict
    features: Optional[dict] = None
    task_id: Optional[str] = config.DEFAULT_TASK


@app.middleware("http")
@limiter.limit("100/minute")
async def add_metrics(request: Request, call_next):
    instrument_request(SERVICE_NAME, request.url.path, request.method)
    return await call_next(request)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/config")
def get_config():
    """Returns non-sensitive service configuration."""
    return {"mlflow_tracking_uri": config.MLFLOW_TRACKING_URI}


def _validate_payload(payload: UpdatePayload):
    if payload.features is None:
        raise HTTPException(
            status_code=400, detail="Invalid payload: features is a required field."
        )

    predictions = payload.proposal.get("predictions")
    if not predictions:
        raise HTTPException(
            status_code=400,
            detail="Invalid payload: proposal.predictions is missing or empty.",
        )

    contradictory = payload.contradiction.get("contradictory")
    if not contradictory:
        raise HTTPException(
            status_code=400,
            detail="Invalid payload: contradiction.contradictory is missing or empty.",
        )


def _persist_dissonance(task_id, input_id, features, proposal, contradiction, loss):
    if loss > 0.01:
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO dissonant_samples (task_id, input_id, features, proposal, "
                "contradiction, loss) VALUES (%s, %s, %s, %s, %s, %s)",
                (
                    task_id,
                    input_id,
                    json.dumps(features),
                    json.dumps(proposal),
                    json.dumps(contradiction),
                    loss,
                ),
            )
            conn.commit()
            cur.close()
            conn.close()
            logger.info(
                f"Persisted dissonant sample {input_id} for task {task_id} to database."
            )
        except Exception as e:
            logger.error(f"Failed to persist dissonant sample to database: {e}")


@app.post("/update")
async def update(payload: UpdatePayload):
    _validate_payload(payload)

    try:
        p = payload.proposal.get("predictions")[0]["p"]
        cp = payload.contradiction.get("contradictory")[0]["p"]
        input_id = payload.proposal.get("input_id")
        task_id = payload.task_id or config.DEFAULT_TASK
    except (KeyError, IndexError) as e:
        logger.error(f"Malformed payload received. Details: {e}")
        raise HTTPException(
            status_code=400, detail="Malformed payload. Missing 'p' key."
        )

    loss = (p - cp) ** 2
    _persist_dissonance(
        task_id,
        input_id,
        payload.features,
        payload.proposal,
        payload.contradiction,
        loss,
    )

    try:
        with mlflow.start_run() as run:
            run_id = run.info.run_id
            mlflow.log_params(payload.features)
            mlflow.log_param("task_id", task_id)
            mlflow.log_metric("loss", loss)
            mlflow.set_tag("input_id", input_id)
            mlflow.set_tag("task_id", task_id)
            mlflow.set_tag("proposer_version", payload.proposal.get("model_version"))
            mlflow.set_tag(
                "critic_version", payload.contradiction.get("critic_version")
            )

            logger.info(
                {
                    "event": "update",
                    "task_id": task_id,
                    "input_id": input_id,
                    "loss": loss,
                }
            )
            return {"status": "updated", "loss": loss, "mlflow_run_id": run_id}
    except Exception as e:
        logger.error(f"Failed to log to MLflow: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to log to MLflow: {e}")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
