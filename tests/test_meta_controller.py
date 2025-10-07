import pytest
from fastapi.testclient import TestClient
import sys
import os
import importlib
from unittest.mock import patch

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.fixture
def client():
    """
    Provides a test client for the meta-controller service. It patches the
    file `open` call to prevent I/O errors during testing.
    """
    with patch("services.meta_controller.main.open"):
        from services.meta_controller.main import app
        importlib.reload(sys.modules['services.meta_controller.main'])
        with TestClient(app) as test_client:
            yield test_client

def test_health_endpoint(client):
    """Tests that the /health endpoint is available."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_config_endpoint(client):
    """Tests that the /config endpoint returns the correct configuration."""
    response = client.get("/config")
    assert response.status_code == 200
    config_data = response.json()
    assert "policy_file_path" in config_data
    assert "d_target" in config_data

def test_get_policy_endpoint(client):
    """Tests the GET /policy endpoint."""
    response = client.get("/policy")
    assert response.status_code == 200
    # The policy is loaded from defaults when `open` is patched
    assert "D_target" in response.json()

@patch("services.meta_controller.main._save_policy")
def test_set_policy_endpoint(mock_save_policy, client):
    """Tests the POST /policy endpoint."""
    new_policy = {"d_target": 0.99}
    response = client.post("/policy", json=new_policy)

    assert response.status_code == 200
    response_data = response.json()
    assert response_data['policy']['d_target'] == 0.99

    # Verify that the function to save the policy was called
    mock_save_policy.assert_called_once()