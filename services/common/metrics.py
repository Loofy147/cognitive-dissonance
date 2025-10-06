from prometheus_client import Counter, Histogram, Gauge
REQUESTS = Counter('service_requests_total', 'Total HTTP requests', ['service', 'path', 'method'])
D_VALUE = Gauge('dissonance_value', 'Current computed dissonance D', ['service'])
REQ_LATENCY = Histogram('service_request_duration_seconds', 'Request latency', ['service', 'path'])
EVALUATION_LOOP_TIMEOUTS_TOTAL = Counter('evaluation_loop_timeouts_total', 'Total timeouts in the evaluation loop', ['service'])


def instrument_request(service: str, path: str, method: str):
    REQUESTS.labels(service=service, path=path, method=method).inc()


def set_d_value(service: str, value: float):
    D_VALUE.labels(service=service).set(value)