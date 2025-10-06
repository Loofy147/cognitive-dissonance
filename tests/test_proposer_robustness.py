import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
import numpy as np
import sys
import os
import importlib

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class OrderSensitiveModel:
    """A mock model that is sensitive to the order of features."""
    def predict_proba(self, features):
        # Correct order is ['f1', 'f2'].
        # This model predicts class B if f1=0 and f2=1.
        if np.array_equal(features, np.array([[0, 1]])):
            return np.array([[0.2, 0.8]])  # High confidence for class B
        else:
            return np.array([[0.5, 0.5]])

@pytest.fixture
def client():
    """
    Provides a test client. It patches `open` and `pickle.load` before
    importing the app to prevent the app from exiting if the model file
    doesn't exist during test setup.
    """
    with patch("builtins.open"), patch("pickle.load"):
        # The module might have been loaded and exited in a previous test.
        # Reloading ensures we get a fresh module with the patches applied.
        import services.proposer.main
        importlib.reload(services.proposer.main)
        from services.proposer.main import app
        yield TestClient(app)

def test_proposer_prediction_is_correct(client):
    """
    Verifies that the proposer's prediction is correct because it uses a
    canonical feature order.
    """
    payload = { "input_id": "test-123", "features": { "f2": 1, "f1": 0 } }
    correct_prediction_p1 = 0.8
    mock_model = OrderSensitiveModel()

    # Patch the model object inside the running app for this specific test.
    with patch('services.proposer.main.model', mock_model):
        response = client.post("/predict", json=payload)

    assert response.status_code == 200
    assert response.json()['predictions'][1]['p'] == pytest.approx(correct_prediction_p1)

def test_proposer_returns_400_on_missing_feature(client):
    """
    Verifies that the proposer returns a 400 Bad Request if a required
    feature is missing.
    """
    payload = { "input_id": "test-456", "features": { "f1": 1 } } # Missing 'f2'
    with patch('services.proposer.main.model', OrderSensitiveModel()):
        response = client.post("/predict", json=payload)

    assert response.status_code == 400
    assert "Missing required feature" in response.json()['detail']

def test_proposer_fails_fast_on_model_load_error():
    """
    Verifies that the service exits immediately if the model cannot be loaded.
    """
    # This test must not use the client fixture.
    # We patch 'open' to fail, then reload the module and check for SystemExit.
    with patch("builtins.open") as mock_open:
        mock_open.side_effect = FileNotFoundError("File not found for testing")
        with pytest.raises(SystemExit) as excinfo:
            # We need to reload the module to trigger the startup code again.
            import services.proposer.main
            importlib.reload(services.proposer.main)

        assert excinfo.value.code == 1, "The application exited with an unexpected code."