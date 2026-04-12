from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from fastapi.testclient import TestClient

from services.critic.main import app as critic_app
from services.proposer.main import app as proposer_app


@pytest.fixture
def mock_mlflow():
    with patch("mlflow.pyfunc.load_model") as mock_load:
        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([0.5])
        mock_model.metadata.run_id = "test_run_id"
        mock_load.return_value = mock_model
        yield mock_load


def test_nemotron_proposer(mock_mlflow):
    with TestClient(proposer_app) as client:
        response = client.post(
            "/predict",
            json={
                "input_id": "test_id",
                "task_id": "nemotron_reasoning",
                "features": {"prompt": "What is 2+2?"},
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "nemotron_reasoning"
        assert data["predictions"][0]["p"] == 0.5


def test_nemotron_critic(mock_mlflow):
    with TestClient(critic_app) as client:
        response = client.post(
            "/contradict",
            json={
                "input_id": "test_id",
                "task_id": "nemotron_reasoning",
                "predictions": [{"class": "A", "p": 0.85}, {"class": "B", "p": 0.15}],
                "model_version": "v1",
                "features": {"prompt": "What is 2+2?"},
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "nemotron_reasoning"
        assert "d" in data
