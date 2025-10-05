import requests
import os
import time

def test_e2e_run_once():
    """
    Tests the /run_once endpoint of the evaluator service.
    This is an end-to-end test that checks the full orchestration flow.
    """
    url = "http://localhost:8003/run_once"

    # The services might still be starting up, so we'll retry a few times.
    for _ in range(10):
        try:
            response = requests.post(url, timeout=10)
            if response.status_code == 200:
                break
        except requests.exceptions.ConnectionError:
            time.sleep(1)
    else:
        assert False, f"Connection to {url} for service evaluator failed after multiple retries"

    assert response.status_code == 200
    response_json = response.json()

    # The orchestration can either complete successfully or be blocked by the safety gate.
    # Both are valid outcomes for this test.
    assert 'status' in response_json
    assert response_json['status'] in ['completed', 'blocked_by_safety']

    if response_json['status'] == 'completed':
        assert 'input_id' in response_json
    elif response_json['status'] == 'blocked_by_safety':
        assert 'reason' in response_json