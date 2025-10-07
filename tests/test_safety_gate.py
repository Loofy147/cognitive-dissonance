import pytest
from fastapi.testclient import TestClient
import sys
import os
import importlib

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.fixture
def client():
    """Provides a test client for the safety_gate service."""
    from services.safety_gate.main import app
    importlib.reload(sys.modules['services.safety_gate.main'])
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
    assert "max_dissonance" in config_data

def test_check_endpoint_allow(client):
    """Tests that the /check endpoint allows a request with low dissonance."""
    payload = {
        "input_id": "test-123",
        "contradictory": [],
        "critic_version": "v1",
        "d": 0.1 # Low dissonance
    }
    response = client.post("/check", json=payload)
    assert response.status_code == 200
    assert response.json() == {"allow": True}

def test_check_endpoint_block(client):
    """Tests that the /check endpoint blocks a request with high dissonance."""
    payload = {
        "input_id": "test-456",
        "contradictory": [],
        "critic_version": "v1",
        "d": 0.9 # High dissonance
    }
    response = client.post("/check", json=payload)
    assert response.status_code == 200
    assert response.json() == {"allow": False, "reason": "dissonance_too_high"}