import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, ANY
import sys
import os
import importlib

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.fixture
def client():
    """
    Provides a test client for the learner service. It patches the mlflow
    dependency *before* the app is created to prevent startup errors.
    """
    with patch("services.learner.main.mlflow"):
        from services.learner.main import app
        # Reload the module to ensure the patch is applied during import
        importlib.reload(sys.modules['services.learner.main'])
        with TestClient(app) as test_client:
            yield test_client

def test_learner_config_endpoint(client):
    """Tests the /config endpoint for the learner service."""
    response = client.get("/config")
    assert response.status_code == 200
    assert "mlflow_tracking_uri" in response.json()

def test_learner_update_endpoint(client):
    """Tests the /update endpoint, verifying MLflow calls."""
    # The client fixture already patches mlflow, but we can get a reference to it
    # to make assertions on the calls.
    with patch("services.learner.main.mlflow") as mock_mlflow:
        valid_payload = {
            "proposal": {
                "input_id": "test-123",
                "predictions": [{"class": "A", "p": 0.6}],
                "model_version": "proposer-v1.2"
            },
            "contradiction": {
                "contradictory": [{"class": "A", "p": 0.8}],
                "critic_version": "critic-v2.1"
            },
            "features": {"f1": 0.5, "f2": 0.5}
        }
        mock_run = mock_mlflow.start_run.return_value.__enter__.return_value
        mock_run.info.run_id = "mock-run-id"

        response = client.post("/update", json=valid_payload)

        assert response.status_code == 200
        assert response.json()['mlflow_run_id'] == "mock-run-id"

        mock_mlflow.start_run.assert_called_once()
        mock_mlflow.log_metric.assert_called_once_with("loss", ANY)
        assert mock_mlflow.set_tag.call_count == 3