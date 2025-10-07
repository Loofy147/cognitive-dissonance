from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
import logging
import mlflow
from contextlib import asynccontextmanager
from services.common.logging_config import configure_logging
from services.common.metrics import instrument_request
from services.common import config
from fastapi import Request

configure_logging()
logger = logging.getLogger('learner')
SERVICE_NAME = 'learner'

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    On startup, configure the MLflow tracking URI and ensure the experiment exists.
    This is done here to avoid making network calls on module import, which
    simplifies testing.
    """
    try:
        mlflow.set_tracking_uri(config.MLFLOW_TRACKING_URI)
        mlflow.set_experiment("dissonance_learning")
        logger.info(f"MLflow tracking URI set to {config.MLFLOW_TRACKING_URI}")
        logger.info("MLflow experiment set to 'dissonance_learning'")
    except Exception as e:
        # If we can't connect to MLflow, we should log it, but the service can still run.
        # It just won't be able to log experiment data.
        logger.error(f"Failed to configure MLflow on startup: {e}")
    yield

app = FastAPI(lifespan=lifespan)

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

@app.get('/config')
def get_config():
    """Returns non-sensitive service configuration."""
    return { "mlflow_tracking_uri": config.MLFLOW_TRACKING_URI }

@app.post('/update')
async def update(payload: UpdatePayload):
    try:
        p = payload.proposal.get('predictions', [])[0]['p']
        cp = payload.contradiction.get('contradictory', [])[0]['p']
        input_id = payload.proposal.get('input_id')
    except (IndexError, KeyError) as e:
        logger.error(f"Malformed payload received. Missing key or empty list. Details: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Malformed payload. Missing key or empty list. Details: {e}"
        )

    loss = (p - cp)**2

    try:
        with mlflow.start_run() as run:
            run_id = run.info.run_id
            logger.info(f"Started MLflow run: {run_id}")

            mlflow.log_params(payload.features)
            mlflow.log_metric("loss", loss)
            mlflow.set_tag("input_id", input_id)
            mlflow.set_tag("proposer_version", payload.proposal.get("model_version"))
            mlflow.set_tag("critic_version", payload.contradiction.get("critic_version"))

            logger.info({
                'event': 'update',
                'input_id': input_id,
                'loss': loss,
                'features': payload.features,
                'mlflow_run_id': run_id
            })

            return {'status':'updated', 'loss': loss, 'mlflow_run_id': run_id}

    except Exception as e:
        logger.error(f"Failed to log to MLflow: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to log to MLflow: {e}")

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)