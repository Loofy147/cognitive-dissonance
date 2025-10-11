import pytest
from fastapi.testclient import TestClient
import sys
import os
import importlib
from unittest.mock import patch, MagicMock

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.fixture
def client():
    """Provides a test client for the evaluator service."""
    from services.evaluator.main import app
    importlib.reload(sys.modules['services.evaluator.main'])
    # The TestClient must be used in a `with` statement to trigger lifespan events.
    with TestClient(app) as test_client:
        yield test_client

def test_health_endpoint(client):
    """Tests that the /health endpoint is available."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "last_run_timestamp" in data

def test_config_endpoint(client):
    """Tests that the /config endpoint returns the correct configuration."""
    response = client.get("/config")
    assert response.status_code == 200
    config_data = response.json()
    assert "proposer_url" in config_data
    assert "critic_url" in config_data
    assert "learner_url" in config_data
    assert "safety_gate_url" in config_data
    assert "loop_timeout_seconds" in config_data

@patch("services.evaluator.main.httpx.AsyncClient")
def test_run_once_endpoint(mock_async_client):
    """Tests the /run_once endpoint, mocking the downstream service calls."""
    from services.evaluator.main import app
    importlib.reload(sys.modules['services.evaluator.main'])

    # Create a mock response object
    mock_response = MagicMock()
    # The .json() method on the response should return a dictionary
    mock_response.json.return_value = {
        "status": "mocked_success",
        "input_id": "mock_id",
        "predictions": [],
        "contradictory": [],
        "allow": True, # For safety gate
    }

    # The post method is async, so its return value should be our mock_response
    mock_async_client.return_value.post = AsyncMock(return_value=mock_response)
    mock_async_client.return_value.aclose = AsyncMock()

    with TestClient(app) as client:
        response = client.post("/run_once")

    assert response.status_code == 200
    response_data = response.json()
    assert response_data['status'] == 'completed'
    assert 'input_id' in response_data

from unittest.mock import patch, MagicMock, AsyncMock

@patch("services.evaluator.main.httpx.AsyncClient")
def test_client_is_reused_across_requests(mock_async_client):
    """
    Tests that the httpx.AsyncClient is reused across multiple requests.
    """
    from services.evaluator.main import app
    importlib.reload(sys.modules['services.evaluator.main'])

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "status": "mocked_success",
        "allow": True,
    }
    # Since the client is now created in the lifespan, we need to configure the mock
    # to behave like an async context manager.
    mock_async_client.return_value.post = AsyncMock(return_value=mock_response)
    mock_async_client.return_value.aclose = AsyncMock()

    with TestClient(app) as client:
        # Make two requests
        client.post("/run_once")
        client.post("/run_once")

    # The client should be created once during the lifespan.
    assert mock_async_client.call_count == 1