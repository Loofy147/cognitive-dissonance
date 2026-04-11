import asyncio
import datetime
import logging
import uuid
from contextlib import asynccontextmanager
from typing import Optional

import httpx
import numpy as np
import pandas as pd
import uvicorn
import os
from fastapi import FastAPI, Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from services.common import config
from services.common.logging_config import configure_logging
from services.common.metrics import (EVALUATION_LOOP_TIMEOUTS_TOTAL,
                                     instrument_request)

configure_logging()
logger = logging.getLogger("evaluator")
SERVICE_NAME = "evaluator"

limiter = Limiter(key_func=get_remote_address)

# Pre-load nemotron data for the loop
try:
    NEMOTRON_DF = pd.read_csv("data/nemotron/train.csv")
    logger.info(f"Evaluator loaded {len(NEMOTRON_DF)} samples for nemotron_reasoning task.")
except Exception as e:
    logger.warning(f"Evaluator could not load nemotron data: {e}")
    NEMOTRON_DF = None


async def _run_orchestration_cycle(app: FastAPI, features: dict, task_id: str):
    input_id = str(uuid.uuid4())

    client = app.state.http_client
    r = await client.post(
        config.PROPOSER_URL,
        json={"input_id": input_id, "task_id": task_id, "features": features},
    )
    proposal = r.json()
    logger.info({"stage": "proposed", "task_id": task_id, "proposal": proposal})

    critic_payload = {**proposal, "features": features, "task_id": task_id}
    c = await client.post(config.CRITIC_URL, json=critic_payload)
    contradiction = c.json()
    logger.info(
        {"stage": "contradicted", "task_id": task_id, "contradiction": contradiction}
    )

    s = await client.post(config.SAFETY_URL, json=contradiction)
    safety = s.json()
    logger.info({"stage": "safety", "result": safety})
    if not safety.get("allow", False):
        return {"status": "blocked_by_safety", "reason": safety.get("reason")}

    learner_payload = {
        "proposal": proposal,
        "contradiction": contradiction,
        "features": features,
        "task_id": task_id,
    }
    u = await client.post(config.LEARNER_URL, json=learner_payload)
    updated = u.json()
    logger.info({"stage": "learner", "updated": updated})

    return {"status": "completed", "input_id": input_id, "task_id": task_id}


async def evaluation_loop(app: FastAPI):
    """The main evaluation loop running in the background."""
    while True:
        try:
            # Cycle through tasks
            for task_id in config.TASKS.keys():
                task_cfg = config.get_task_config(task_id)

                if task_id == "nemotron_reasoning" and NEMOTRON_DF is not None:
                    # Sample from the real dataset
                    sample = NEMOTRON_DF.sample(1).iloc[0]
                    features = {"prompt": sample["prompt"]}
                else:
                    features = {
                        k: round(np.random.uniform(0, 1), 2)
                        for k in task_cfg["feature_names"]
                    }

                    # Domain specific adjustments for diabetes
                    if task_id == "diabetes":
                        if "age" in features:
                            features["age"] = round(np.random.uniform(20, 80), 0)
                        if "gender" in features:
                            features["gender"] = float(np.random.choice([0, 1]))

                await asyncio.wait_for(
                    _run_orchestration_cycle(app, features, task_id),
                    timeout=config.EVALUATOR_LOOP_TIMEOUT_SECONDS,
                )
                app.state.last_run_timestamp = datetime.datetime.now(
                    datetime.UTC
                ).isoformat()
                await asyncio.sleep(1.0)
        except asyncio.TimeoutError:
            logger.warning(
                f"run_once call timed out after {config.EVALUATOR_LOOP_TIMEOUT_SECONDS} seconds."
            )
            EVALUATION_LOOP_TIMEOUTS_TOTAL.labels(service=SERVICE_NAME).inc()
        except asyncio.CancelledError:
            logger.info("Evaluation loop cancelled.")
            break
        except Exception:
            logger.exception("loop error")
        await asyncio.sleep(2.0)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application state and background tasks."""
    app.state.last_run_timestamp = None
    app.state.http_client = httpx.AsyncClient(timeout=10.0)
    loop = asyncio.get_event_loop()
    task = loop.create_task(evaluation_loop(app))
    yield
    task.cancel()
    await app.state.http_client.aclose()
    try:
        await task
    except asyncio.CancelledError:
        logger.info("Evaluation loop task successfully cancelled.")


app = FastAPI(lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.middleware("http")
@limiter.limit("100/minute")
async def add_metrics(request: Request, call_next):
    instrument_request(SERVICE_NAME, request.url.path, request.method)
    return await call_next(request)


@app.get("/health")
def health(request: Request):
    return {"status": "ok", "last_run_timestamp": request.app.state.last_run_timestamp}


@app.get("/config")
def get_config():
    """Returns non-sensitive service configuration."""
    return {
        "tasks": list(config.TASKS.keys()),
        "proposer_url": config.PROPOSER_URL,
        "critic_url": config.CRITIC_URL,
        "learner_url": config.LEARNER_URL,
        "safety_gate_url": config.SAFETY_URL,
        "loop_timeout_seconds": config.EVALUATOR_LOOP_TIMEOUT_SECONDS,
    }


class RunOnceRequest(pd.Series): # Just a dummy for pydantic if needed
    pass

from pydantic import BaseModel
class RunOnceRequest(BaseModel):
    features: dict
    task_id: Optional[str] = config.DEFAULT_TASK


@app.post("/run_once")
async def run_once_endpoint(request: Request, body: RunOnceRequest):
    """Endpoint to trigger a single orchestration cycle for testing."""
    task_id = body.task_id or config.DEFAULT_TASK
    return await _run_orchestration_cycle(request.app, body.features, task_id)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
