import requests
import pytest
import time

META_CONTROLLER_URL = "http://localhost:8005"

@pytest.fixture(scope="module")
def meta_controller_service():
    """Fixture to check if the meta-controller service is available."""
    try:
        response = requests.get(f"{META_CONTROLLER_URL}/health", timeout=5)
        response.raise_for_status()
    except (requests.exceptions.ConnectionError, requests.exceptions.HTTPError) as e:
        pytest.fail(f"Meta-controller service is not running or not healthy: {e}")
    return META_CONTROLLER_URL

def test_policy_persistence(meta_controller_service):
    """
    Tests the policy update and persistence logic.
    - Fetches the initial policy.
    - Updates the policy with new values.
    - Fetches the policy again to confirm the update was successful.

    Note: This test confirms the API behavior. True persistence testing would require
    restarting the service, which is outside the scope of this test.
    """
    # 1. Get the original policy
    original_response = requests.get(f"{meta_controller_service}/policy", timeout=5)
    assert original_response.status_code == 200
    original_policy = original_response.json()
    assert "D_target" in original_policy

    # 2. Update the policy with a new value
    new_d_target = original_policy["D_target"] + 0.1
    update_payload = {"D_target": new_d_target}

    update_response = requests.post(
        f"{meta_controller_service}/policy", json=update_payload, timeout=5
    )
    assert update_response.status_code == 200
    updated_policy_from_post = update_response.json()["policy"]
    assert updated_policy_from_post["D_target"] == new_d_target

    # 3. Get the policy again to confirm the change is "persisted" for the session
    get_response = requests.get(f"{meta_controller_service}/policy", timeout=5)
    assert get_response.status_code == 200
    persisted_policy = get_response.json()
    assert persisted_policy["D_target"] == new_d_target

    # 4. Restore the original policy to leave the system in a clean state
    restore_payload = {"D_target": original_policy["D_target"]}
    restore_response = requests.post(
        f"{meta_controller_service}/policy", json=restore_payload, timeout=5
    )
    assert restore_response.status_code == 200