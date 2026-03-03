import importlib  # noqa: F401  # noqa: F401
import os
import sys
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


@pytest.fixture
def client():
    # Patch EVERYTHING that could hang
    with patch("services.learner.main.mlflow"), patch(
        "services.learner.main.psycopg2.connect"
    ):
        from services.learner.main import app  # noqa: E402

        # DO NOT RELOAD, just use if already loaded or load fresh once
        # importlib.reload(sys.modules['services.learner.main'])
        with TestClient(app) as test_client:
            yield test_client


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200


def test_learner_update_endpoint(client):
    with patch("services.learner.main.mlflow") as mock_mlflow:
        valid_payload = {
            "proposal": {
                "input_id": "test-123",
                "predictions": [{"class": "A", "p": 0.6}],
                "model_version": "proposer-v1.2",
            },
            "contradiction": {
                "contradictory": [{"class": "A", "p": 0.8}],
                "critic_version": "critic-v2.1",
            },
            "features": {"f1": 0.5, "f2": 0.5},
            "task_id": "diabetes",
        }
        mock_run = mock_mlflow.start_run.return_value.__enter__.return_value
        mock_run.info.run_id = "mock-run-id"
        response = client.post("/update", json=valid_payload)
        assert response.status_code == 200
