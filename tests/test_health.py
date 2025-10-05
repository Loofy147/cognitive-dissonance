import requests
import os
import time

def test_services_health():
    services = [
        "proposer",
        "critic",
        "evaluator",
        "learner",
        "meta-controller",
        "safety-gate",
    ]
    for i, service in enumerate(services):
        url = f"http://localhost:800{i+1}/health"
        for _ in range(10): # retry for 10 seconds
            try:
                r = requests.get(url, timeout=1)
                if r.status_code == 200:
                    assert r.json().get('status') == 'ok'
                    print(f"Service {service} is healthy at {url}")
                    break
            except requests.exceptions.ConnectionError:
                time.sleep(1)
        else:
            assert False, f"Connection to {url} for service {service} failed after multiple retries"