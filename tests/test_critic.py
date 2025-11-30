import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
import sys
import os
import importlib

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.fixture
def client():
    """
    Provides a test client for the critic service. It patches the MLflow
    model loading dependencies to prevent startup failures during testing.
    """
    with patch("mlflow.pyfunc.load_model") as mock_load_model:
        mock_load_model.return_value.metadata.run_id = "test-run-id"
        from services.critic.main import app
        importlib.reload(sys.modules['services.critic.main'])
        with TestClient(app) as test_client:
            yield test_client

def test_health_endpoint(client):
    """Tests that the /health endpoint is available."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_config_endpoint(client):
    """Tests that the /config endpoint returns the correct configuration."""
    client.app.state.model_version = "test-version"
    response = client.get("/config")
    assert response.status_code == 200
    config_data = response.json()
    assert "model_name" in config_data
    assert config_data["model_version"] == "test-version"
    assert "mlflow_tracking_uri" in config_data

def test_contradict_endpoint_with_model(client):
    """Tests a successful contradiction from the /contradict endpoint."""
    mock_model = client.app.state.model
    mock_model.predict.return_value = [0.3] # MLflow pyfunc models return a single value

    payload = {
        "input_id": "test-123",
        "predictions": [{"class": "A", "p": 0.8}],
        "model_version": "proposer-v1",
        "features": {"f1": 1, "f2": 0}
    }
    response = client.post("/contradict", json=payload)

    assert response.status_code == 200
    response_data = response.json()
    assert response_data['input_id'] == "test-123"
    assert response_data['contradictory'][0]['p'] == 0.3

def test_fail_fast_on_model_load_error():
    """
    Verifies that the service exits immediately if the model cannot be loaded.
    """
    with patch("mlflow.pyfunc.load_model", side_effect=Exception("MLflow error")), \
         patch("sys.exit") as mock_exit:

        import services.critic.main
        importlib.reload(services.critic.main)

        with TestClient(services.critic.main.app):
            pass

        mock_exit.assert_called_once_with(1)
