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
    file, service health, and configuration checks pass.
    """
    with patch('os.path.exists', return_value=True):
        for url in config.HEALTH_CHECK_URLS.values():
            httpx_mock.add_response(url=url, json={"status": "ok"})
        for url in config.CONFIG_URLS.values():
            httpx_mock.add_response(url=url, json={"some_config": "some_value"})

        response = client.post("/audit")

    assert response.status_code == 200
    response_data = response.json()
    assert len(response_data['findings']) == 0

@pytest.mark.asyncio
async def test_audit_one_service_misconfigured(client, httpx_mock):
    """
    Verifies that the auditor correctly reports a service that returns
    an empty configuration.
    """
    with patch('os.path.exists', return_value=True):
        # Mock all health checks as healthy
        for url in config.HEALTH_CHECK_URLS.values():
            httpx_mock.add_response(url=url, json={"status": "ok"})

        # Mock config checks, with one returning an empty JSON object
        for service, url in config.CONFIG_URLS.items():
            if service == "proposer":
                httpx_mock.add_response(url=url, json={}) # Empty config
            else:
                httpx_mock.add_response(url=url, json={"some_config": "some_value"})

        response = client.post("/audit")

    assert response.status_code == 200
    response_data = response.json()
    assert len(response_data['findings']) == 1
    finding = response_data['findings'][0]
    assert finding['id'] == 'CONFIG_EMPTY'
    assert "Service 'proposer' returned an empty configuration" in finding['detail']

@pytest.mark.asyncio
async def test_audit_combines_all_finding_types(client, httpx_mock):
    """
    Verifies that the auditor correctly combines findings from file, health,
    and configuration checks.
    """
    # 1. Mock file system to report one missing file
    def mock_exists(path):
        return 'critic' in path

    with patch('os.path.exists', side_effect=mock_exists):
        # 2. Mock one service as unreachable
        httpx_mock.add_response(url=config.HEALTH_CHECK_URLS['critic'], status_code=500)
        # 3. Mock one service as misconfigured
        httpx_mock.add_response(url=config.CONFIG_URLS['meta-controller'], json={})
        # 4. Mock the rest as healthy
        for service, url in config.HEALTH_CHECK_URLS.items():
            if service != 'critic': httpx_mock.add_response(url=url, json={"status": "ok"})
        for service, url in config.CONFIG_URLS.items():
            if service != 'meta-controller': httpx_mock.add_response(url=url, json={"some_config": "some_value"})

        response = client.post("/audit")

    assert response.status_code == 200
    response_data = response.json()
    # Expect 1 file + 1 health + 1 config finding = 3 total
    assert len(response_data['findings']) == 3

    finding_ids = {f['id'] for f in response_data['findings']}
    assert 'MODEL_FILE_MISSING' in finding_ids
    assert 'SERVICE_UNHEALTHY' in finding_ids
    assert 'CONFIG_EMPTY' in finding_ids