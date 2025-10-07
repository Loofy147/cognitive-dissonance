import pytest
from fastapi.testclient import TestClient
from services.auditor.main import app, _check_evaluator_liveness, EVALUATOR_LOOP_STUCK_THRESHOLD_SECONDS
from services.common import config
import datetime
import httpx

@pytest.fixture
def mock_httpx(httpx_mock):
    """Fixture to mock httpx requests."""
    return httpx_mock

def test_audit_endpoint(mock_httpx):
    """Test the main /audit endpoint to ensure it runs without errors."""
    # Mock all external services to be healthy to isolate the auditor's logic
    for service, url in config.HEALTH_CHECK_URLS.items():
        mock_httpx.add_response(url=url, method="GET", json={"status": "ok", "last_run_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()})

    # The auditor calls the evaluator's health endpoint twice (once for the generic health check, once for the specific liveness check)
    # so we need to add a second response for it.
    mock_httpx.add_response(url=config.HEALTH_CHECK_URLS["evaluator"], method="GET", json={"status": "ok", "last_run_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()})

    for service, url in config.CONFIG_URLS.items():
        # Return a simple dict to avoid the "CONFIG_EMPTY" finding
        mock_httpx.add_response(url=url, method="GET", json={"config": "valid"})

    with TestClient(app) as client:
        response = client.post("/audit")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        # With all services healthy, we expect no findings related to service health/config
        # There might be MODEL_FILE_MISSING findings, which is fine for this test.
        finding_ids = [f["id"] for f in data["findings"]]
        assert "SERVICE_UNHEALTHY" not in finding_ids
        assert "SERVICE_UNREACHABLE" not in finding_ids
        assert "CONFIG_EMPTY" not in finding_ids


@pytest.mark.asyncio
async def test_check_evaluator_liveness_not_run_yet(mock_httpx):
    """Test the case where the evaluator has not completed a cycle yet."""
    evaluator_health_url = config.HEALTH_CHECK_URLS["evaluator"]
    mock_httpx.add_response(url=evaluator_health_url, method="GET", json={"status": "ok", "last_run_timestamp": None})

    async with httpx.AsyncClient() as async_client:
        finding = await _check_evaluator_liveness(async_client)

    assert finding is not None
    assert finding["id"] == "EVALUATOR_NOT_RUN"


@pytest.mark.asyncio
async def test_check_evaluator_liveness_stuck(mock_httpx):
    """Test the case where the evaluator loop is stuck."""
    evaluator_health_url = config.HEALTH_CHECK_URLS["evaluator"]
    stuck_timestamp = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=EVALUATOR_LOOP_STUCK_THRESHOLD_SECONDS + 5)).isoformat()
    mock_httpx.add_response(url=evaluator_health_url, method="GET", json={"status": "ok", "last_run_timestamp": stuck_timestamp})

    async with httpx.AsyncClient() as async_client:
        finding = await _check_evaluator_liveness(async_client)

    assert finding is not None
    assert finding["id"] == "EVALUATOR_STUCK"


@pytest.mark.asyncio
async def test_check_evaluator_liveness_healthy(mock_httpx):
    """Test the case where the evaluator is running normally."""
    evaluator_health_url = config.HEALTH_CHECK_URLS["evaluator"]
    healthy_timestamp = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=10)).isoformat()
    mock_httpx.add_response(url=evaluator_health_url, method="GET", json={"status": "ok", "last_run_timestamp": healthy_timestamp})

    async with httpx.AsyncClient() as async_client:
        finding = await _check_evaluator_liveness(async_client)

    assert finding is None

@pytest.mark.asyncio
async def test_check_evaluator_liveness_unreachable(mock_httpx):
    """Test that no finding is returned if the evaluator is unreachable, as another check handles this."""
    evaluator_health_url = config.HEALTH_CHECK_URLS["evaluator"]
    mock_httpx.add_exception(httpx.RequestError("Connection failed", request=None), url=evaluator_health_url, method="GET")

    async with httpx.AsyncClient() as async_client:
        finding = await _check_evaluator_liveness(async_client)

    assert finding is None