import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
import numpy as np
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the FastAPI app instance from the critic service
from services.critic.main import app

class OrderSensitiveModel:
    """A mock model that is sensitive to the order of features."""
    def predict_proba(self, features):
        # This model's prediction depends on the order of the features.
        # If features are [1, 0] (f1=1, f2=0), it predicts class A.
        if np.array_equal(features, np.array([[1, 0]])):
            return np.array([[0.9, 0.1]])  # High confidence for class A
        else:
            return np.array([[0.5, 0.5]])  # Neutral for any other case

@pytest.fixture
def client():
    """Provides a test client for the critic service's FastAPI app."""
    return TestClient(app)

def test_critic_prediction_is_correct_with_any_feature_order(client):
    """
    Verifies that the critic's prediction is correct because it now uses a
    canonical feature order, regardless of the order in the payload.
    """
    # The model expects features in the order ['f1', 'f2'].
    # The correct feature vector should be [1, 0].
    payload = {
        "input_id": "test-123",
        "predictions": [{"class": "A", "p": 0.6}],
        "model_version": "proposer-v1",
        "features": {
            "f2": 0,  # Non-alphabetical order
            "f1": 1
        }
    }

    # The fixed implementation should ignore the payload order and build the
    # correct feature vector [1, 0], resulting in a prediction of p0=0.9.
    correct_prediction_p0 = 0.9
    mock_model = OrderSensitiveModel()

    with patch('services.critic.main.model', mock_model):
        response = client.post("/contradict", json=payload)

    assert response.status_code == 200
    response_data = response.json()
    assert response_data['contradictory'][0]['p'] == pytest.approx(correct_prediction_p0), \
        "The critic returned an incorrect prediction, meaning the feature ordering fix is not working."

def test_critic_returns_400_on_missing_feature(client):
    """
    Verifies that the critic returns a 400 Bad Request if a required
    feature is missing from the payload.
    """
    # This payload is missing the required 'f2' feature.
    payload = {
        "input_id": "test-456",
        "predictions": [{"class": "A", "p": 0.7}],
        "model_version": "proposer-v1",
        "features": {
            "f1": 1
        }
    }

    mock_model = OrderSensitiveModel()

    with patch('services.critic.main.model', mock_model):
        response = client.post("/contradict", json=payload)

    assert response.status_code == 400, "The service did not return a 400 error for a missing feature."
    response_data = response.json()
    assert "Missing required feature" in response_data['detail'], \
        "The error detail did not contain the expected message for a missing feature."