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
    Provides a test client for the critic service. It patches the model
    loading to prevent startup failures during testing.
    """
    with patch("services.critic.main.open"), patch("services.critic.main.pickle.load"):
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
    assert "model_path" in config_data
    assert config_data["model_version"] == "test-version"

def test_contradict_endpoint_with_model(client):
    """Tests a successful contradiction from the /contradict endpoint."""
    mock_model = client.app.state.model
    mock_model.predict_proba.return_value = [[0.3, 0.7]]

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

def test_contradict_endpoint_fallback_logic():
    """
    Tests the fallback logic when the model fails to load.
    We create a client where the model loading is explicitly made to fail.
    """
    with patch("services.critic.main.open") as mock_open:
        mock_open.side_effect = FileNotFoundError

        import services.critic.main
        importlib.reload(services.critic.main)
        from services.critic.main import app

        with TestClient(app) as client:
            payload = {
                "input_id": "test-fallback",
                "predictions": [{"class": "A", "p": 0.9}],
                "model_version": "proposer-v1",
                "features": {"f1": 1, "f2": 0}
            }
            response = client.post("/contradict", json=payload)

            assert response.status_code == 200
            # Fallback logic is `1.0 - p0 + 0.05`
            expected_fallback_p = 1.0 - 0.9 + 0.05
            assert response.json()['contradictory'][0]['p'] == pytest.approx(expected_fallback_p)