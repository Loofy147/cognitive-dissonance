import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import datetime
import sys
import os
import importlib

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.auditor.main import app
from services.common import config

@pytest.fixture
def mock_httpx(httpx_mock):
    return httpx_mock

def test_audit_endpoint(mock_httpx):
    # Mock MLflow check to pass
    with patch("services.auditor.main._check_mlflow_connectivity", return_value=None):
        for service, url in config.HEALTH_CHECK_URLS.items():
            mock_httpx.add_response(url=url, method="GET", json={"status": "ok", "last_run_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()})

        # Second health check for evaluator liveness
        mock_httpx.add_response(url=config.HEALTH_CHECK_URLS["evaluator"], method="GET", json={"status": "ok", "last_run_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()})

        for service, url in config.CONFIG_URLS.items():
            mock_httpx.add_response(url=url, method="GET", json={"valid": True})

        with TestClient(app) as client:
            response = client.post("/audit")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "completed"
