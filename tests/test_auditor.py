import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
import sys
import os
import httpx

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.auditor.main import app
from services.common import config

@pytest.fixture
def client():
    """Provides a test client for the auditor service's FastAPI app."""
    return TestClient(app)

@pytest.mark.asyncio
async def test_audit_all_systems_healthy(client, httpx_mock):
    """
    Verifies that the /audit endpoint returns no findings when all
    file and service health checks pass.
    """
    with patch('os.path.exists', return_value=True):
        for url in config.HEALTH_CHECK_URLS.values():
            httpx_mock.add_response(url=url, json={"status": "ok"})

        response = client.post("/audit")

    assert response.status_code == 200
    response_data = response.json()
    assert len(response_data['findings']) == 0

@pytest.mark.asyncio
async def test_audit_one_service_unhealthy(client, httpx_mock):
    """
    Verifies that the /audit endpoint correctly reports a service that
    returns a non-200 status code.
    """
    with patch('os.path.exists', return_value=True):
        for service, url in config.HEALTH_CHECK_URLS.items():
            if service == "proposer":
                httpx_mock.add_response(url=url, status_code=503)
            else:
                httpx_mock.add_response(url=url, json={"status": "ok"})

        response = client.post("/audit")

    assert response.status_code == 200
    response_data = response.json()
    assert len(response_data['findings']) == 1
    finding = response_data['findings'][0]
    assert finding['id'] == 'SERVICE_UNHEALTHY'
    assert "returned a non-200 status code: 503" in finding['detail']

@pytest.mark.asyncio
async def test_audit_one_service_unreachable(client, httpx_mock):
    """
    Verifies that the /audit endpoint correctly reports a service that
    is completely unreachable.
    """
    with patch('os.path.exists', return_value=True):
        for service, url in config.HEALTH_CHECK_URLS.items():
            if service == "critic":
                httpx_mock.add_exception(httpx.ConnectError("Connection refused"), url=url)
            else:
                httpx_mock.add_response(url=url, json={"status": "ok"})

        response = client.post("/audit")

    assert response.status_code == 200
    response_data = response.json()
    assert len(response_data['findings']) == 1
    finding = response_data['findings'][0]
    assert finding['id'] == 'SERVICE_UNREACHABLE'
    assert "Service 'critic' is unreachable" in finding['detail']

@pytest.mark.asyncio
async def test_audit_combines_file_and_service_findings(client, httpx_mock):
    """
    Verifies that the auditor correctly combines findings from both
    file system checks and service health checks.
    """
    with patch('os.path.exists', return_value=False):
        # Mock a specific response for each service URL to make the test pass.
        for url in config.HEALTH_CHECK_URLS.values():
            httpx_mock.add_response(url=url, status_code=500)

        response = client.post("/audit")

    assert response.status_code == 200
    response_data = response.json()
    # Expect 2 file findings + 6 service findings = 8 total
    assert len(response_data['findings']) == 8

    finding_ids = {f['id'] for f in response_data['findings']}
    assert 'MODEL_FILE_MISSING' in finding_ids
    assert 'SERVICE_UNHEALTHY' in finding_ids