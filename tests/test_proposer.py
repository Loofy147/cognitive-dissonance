import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, ANY
import sys
import os
import importlib

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# This fixture is key. It patches dependencies *before* creating the app.
@pytest.fixture
def client():
    """
    Provides a test client for the proposer service. It patches the model
    loading dependencies to prevent startup failures during testing.
    """
    # Patches are applied to the module before it's reloaded and the app is created.
    with patch("services.proposer.main.open"), patch("services.proposer.main.pickle.load"):
        from services.proposer.main import app
        importlib.reload(sys.modules['services.proposer.main'])

        with TestClient(app) as test_client:
            yield test_client

def test_health_endpoint(client):
    """Tests that the /health endpoint is available and healthy."""
    # The lifespan event sets app.state.model. The health check verifies it.
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_config_endpoint(client):
    """Tests that the /config endpoint returns the correct configuration."""
    response = client.get("/config")
    assert response.status_code == 200
    config_data = response.json()
    assert "model_path" in config_data
    assert "model_version" in config_data

def test_predict_endpoint(client):
    """Tests a successful prediction from the /predict endpoint."""
    # Mock the model's prediction method on the app's state
    mock_model = client.app.state.model
    mock_model.predict_proba.return_value = [[0.8, 0.2]]

    payload = { "input_id": "test-123", "features": {"f1": 1, "f2": 0} }
    response = client.post("/predict", json=payload)

    assert response.status_code == 200
    response_data = response.json()
    assert response_data['input_id'] == "test-123"
    assert response_data['predictions'][0]['p'] == 0.8

def test_fail_fast_on_model_load_error():
    """
    Verifies that the service exits immediately if the model cannot be loaded.
    This test does NOT use the client fixture because we want the app to fail.
    """
    # Patch open to simulate a missing model file, and patch sys.exit to verify it's called.
    with patch("builtins.open", side_effect=FileNotFoundError), \
         patch("sys.exit") as mock_exit:

        # Reload the proposer's main module to apply the patch at import time.
        import services.proposer.main
        importlib.reload(services.proposer.main)

        # The TestClient context manager triggers the lifespan startup.
        # The startup should call our mocked sys.exit. Because the mock doesn't
        # actually exit, the app will start normally.
        with TestClient(services.proposer.main.app):
            pass  # The app startup will proceed without exiting.

        # Verify that the application tried to exit with status code 1.
        mock_exit.assert_called_once_with(1)