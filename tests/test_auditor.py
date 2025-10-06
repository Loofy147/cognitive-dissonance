import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.auditor.main import app

@pytest.fixture
def client():
    """Provides a test client for the auditor service's FastAPI app."""
    return TestClient(app)

def test_audit_with_no_issues(client):
    """
    Verifies that the /audit endpoint returns no findings when all
    system checks pass.
    """
    # Mock os.path.exists to return True for all checks.
    with patch('os.path.exists', return_value=True):
        response = client.post("/audit")

    assert response.status_code == 200
    response_data = response.json()
    assert response_data['status'] == 'completed'
    assert len(response_data['findings']) == 0, "Expected no findings, but some were returned."

def test_audit_with_one_model_missing(client):
    """
    Verifies that the /audit endpoint correctly reports a single missing model file.
    """
    # Mock os.path.exists to simulate the proposer model missing.
    def mock_exists(path):
        if 'proposer.pkl' in path:
            return False  # Proposer model is missing
        return True  # Other files (like critic.pkl) exist

    with patch('os.path.exists', side_effect=mock_exists):
        response = client.post("/audit")

    assert response.status_code == 200
    response_data = response.json()
    assert len(response_data['findings']) == 1, "Expected exactly one finding."
    finding = response_data['findings'][0]
    assert finding['id'] == 'MODEL_FILE_MISSING'
    assert 'Proposer model file not found' in finding['detail']

def test_audit_with_both_models_missing(client):
    """
    Verifies that the /audit endpoint correctly reports both missing model files.
    """
    # Mock os.path.exists to always return False, simulating all files missing.
    with patch('os.path.exists', return_value=False):
        response = client.post("/audit")

    assert response.status_code == 200
    response_data = response.json()
    assert len(response_data['findings']) == 2, "Expected exactly two findings."

    # Check for both expected error messages
    details = [f['detail'] for f in response_data['findings']]
    assert any('Proposer model file not found' in d for d in details)
    assert any('Critic model file not found' in d for d in details)