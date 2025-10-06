import pytest
from fastapi.testclient import TestClient
import sys
import os
import importlib
from unittest.mock import patch

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# A list of service modules to test
# We patch 'open' and 'pickle.load' to prevent startup failures
SERVICE_MODULE_NAMES = [
    "services.proposer.main",
    "services.critic.main",
    "services.evaluator.main",
    "services.learner.main",
    "services.meta_controller.main",
    "services.safety_gate.main",
]

@pytest.mark.parametrize("module_name", SERVICE_MODULE_NAMES)
def test_config_endpoint_for_service(module_name):
    """
    A parameterized test to verify the /config endpoint for each service.
    """
    with patch("builtins.open"), patch("pickle.load"):
        # Import the module dynamically
        module = importlib.import_module(module_name)
        # Reload to apply patches
        importlib.reload(module)
        app = getattr(module, 'app')
        client = TestClient(app)

        response = client.get("/config")
        assert response.status_code == 200

        config_data = response.json()
        assert isinstance(config_data, dict)

        # The learner service is the only one expected to have an empty config
        if "learner" in module_name:
            assert config_data == {}
        else:
            assert len(config_data) > 0, f"Expected config for {module_name} to not be empty."