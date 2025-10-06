import requests
import pytest

PROPOSER_URL = "http://localhost:8001"

@pytest.fixture(scope="module")
def proposer_service():
    """Fixture to check if the proposer service is available."""
    try:
        response = requests.get(f"{PROPOSER_URL}/health", timeout=5)
        response.raise_for_status()
    except (requests.exceptions.ConnectionError, requests.exceptions.HTTPError) as e:
        pytest.fail(f"Proposer service is not running or not healthy: {e}")
    return PROPOSER_URL

def test_proposer_predict(proposer_service):
    """
    Tests the /predict endpoint of the proposer service.
    - Asserts that the response is successful (200 OK).
    - Validates the structure of the prediction response.
    - Checks that the probabilities sum to approximately 1.0.
    """
    # Define a sample input payload
    payload = {
        "input_id": "test-123",
        "features": {"f1": 0.5, "f2": 1.5}
    }

    # Make a request to the predict endpoint
    response = requests.post(f"{proposer_service}/predict", json=payload, timeout=5)

    # Assertions
    assert response.status_code == 200

    data = response.json()
    assert data["input_id"] == "test-123"
    assert "predictions" in data
    assert "model_version" in data

    predictions = data["predictions"]
    assert isinstance(predictions, list)
    assert len(predictions) == 2

    # Check the format of each prediction
    for p in predictions:
        assert "class" in p
        assert "p" in p
        assert isinstance(p["p"], float)

    # Check that probabilities are valid
    prob_sum = sum(p["p"] for p in predictions)
    assert pytest.approx(prob_sum, 0.001) == 1.0