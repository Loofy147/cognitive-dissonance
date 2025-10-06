import pytest
from fastapi.testclient import TestClient
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.learner.main import app

@pytest.fixture
def client():
    """Provides a test client for the learner service's FastAPI app."""
    return TestClient(app)

def test_learner_returns_400_with_malformed_payload(client):
    """
    Verifies that the learner service returns a 400 Bad Request if the
    'predictions' list in the payload is empty.
    """
    malformed_payload = {
        "proposal": {
            "input_id": "test-123",
            "predictions": []  # Empty list should be handled gracefully
        },
        "contradiction": {
            "contradictory": [{"class": "A", "p": 0.8}]
        },
        "features": {"f1": 0, "f2": 1}
    }

    response = client.post("/update", json=malformed_payload)

    # Assert that the service now returns a 400 error instead of crashing.
    assert response.status_code == 400, \
        "The service did not return a 400 error for the malformed payload."
    assert "Malformed payload" in response.json()['detail']

def test_learner_succeeds_with_valid_payload(client):
    """
    Verifies that the learner service still processes a valid payload correctly.
    """
    valid_payload = {
        "proposal": {
            "input_id": "test-456",
            "predictions": [{"class": "A", "p": 0.6}]
        },
        "contradiction": {
            "contradictory": [{"class": "A", "p": 0.8}]
        },
        "features": {"f1": 0.5, "f2": 0.5}
    }

    response = client.post("/update", json=valid_payload)

    assert response.status_code == 200, "The service failed to process a valid payload."
    response_data = response.json()
    assert response_data['status'] == 'updated'
    assert 'loss' in response_data
    expected_loss = (0.6 - 0.8)**2
    assert response_data['loss'] == pytest.approx(expected_loss)