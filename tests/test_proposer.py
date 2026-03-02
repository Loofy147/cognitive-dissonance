import importlib  # noqa: F401  # noqa: F401
import os
import sys
from unittest.mock import ANY, patch

import pytest
from fastapi.testclient import TestClient

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.common import config  # noqa: E402


@pytest.fixture
def client():
    """Provides a test client for the proposer service."""
    os.environ["TEST_MODE"] = "1"
    with patch("mlflow.pyfunc.load_model") as mock_load_model:
        # Mock the metadata attribute of the loaded model
        mock_load_model.return_value.metadata.run_id = "test-run-id"
        from services.proposer.main import app

        # Use context manager to trigger lifespan
        with TestClient(app) as test_client:
            yield test_client


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200


def test_predict_endpoint(client):
    # Retrieve the mock model that was loaded during lifespan
    mock_model = client.app.state.proposer.models["diabetes"]
    mock_model.predict.return_value = [0.8]
    task_cfg = config.get_task_config("diabetes")
    features = {name: 0.0 for name in task_cfg["feature_names"]}
    payload = {"input_id": "test-123", "task_id": "diabetes", "features": features}
    response = client.post("/predict", json=payload)
    assert response.status_code == 200
    assert response.json()["predictions"][0]["p"] == 0.8
