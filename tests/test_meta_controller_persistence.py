import pytest
import os
import json
import sys
from unittest.mock import patch

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# We need to import the function we are testing
from services.meta_controller.main import _save_policy

def test_save_policy_creates_directory_and_file(tmp_path):
    """
    This test verifies that _save_policy correctly creates the parent
    directory if it does not exist and saves the policy file.
    """
    # 1. Define a path in a non-existent subdirectory of the temp folder
    non_existent_dir = tmp_path / "policy_data"
    policy_file_path = non_existent_dir / "policy.json"

    # Ensure the directory does not exist initially
    assert not os.path.exists(non_existent_dir)

    # 2. Define some dummy policy data
    dummy_policy = {"key": "value", "level": 1}

    # 3. Patch the config to use our temporary, non-existent path
    with patch('services.meta_controller.main.config.POLICY_FILE_PATH', str(policy_file_path)):
        # 4. Call the function that is supposed to save the policy
        _save_policy(dummy_policy)

    # 5. Assert that the file was created successfully
    assert os.path.exists(policy_file_path), "The policy file was not created."

    # 6. Verify the content of the created file
    with open(policy_file_path, 'r') as f:
        saved_data = json.load(f)

    assert saved_data == dummy_policy, "The saved policy data does not match the original data."