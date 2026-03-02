import importlib  # noqa: F401  # noqa: F401
import os
import sys
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.common import config  # noqa: E402


@pytest.fixture
def client():
    """Provides a test client for the critic service."""
    os.environ["TEST_MODE"] = "1"
    with patch("mlflow.pyfunc.load_model") as mock_load_model:
        mock_load_model.return_value.metadata.run_id = "test-run-id"
        from services.critic.main import app

        with TestClient(app) as test_client:
            yield test_client


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200


def test_contradict_endpoint_with_model(client):
    mock_model = client.app.state.critic.models["diabetes"]
    mock_model.predict.return_value = [0.3]
    task_cfg = config.get_task_config("diabetes")
    features = {name: 0.0 for name in task_cfg["feature_names"]}
    payload = {
        "input_id": "test-123",
        "task_id": "diabetes",
        "predictions": [{"class": "A", "p": 0.8}],
        "model_version": "proposer-v1",
        "features": features,
    }
    response = client.post("/contradict", json=payload)
    assert response.status_code == 200
    assert response.json()["contradictory"][0]["p"] == 0.3
