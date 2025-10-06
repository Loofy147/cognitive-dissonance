# System Evolution & Future Roadmap

This document tracks the major improvements made to the Self-Cognitive-Dissonance System to enhance its robustness, reliability, and observability, evolving it from a proof-of-concept to a more production-ready application. It also outlines a roadmap for future development.

## Phase 1: Hardening the Core Logic

The initial phase of work focused on identifying and fixing fragile approaches in the core logic of the microservices. Each fix was verified with new, targeted unit tests.

### Summary of Improvements

*   **Fail-Fast Startup:** Services that depend on critical resources (like model files) now exit immediately if those resources are not available at startup. This prevents services from running in a silent, broken state.
    *   *Affected Service:* `proposer`

*   **Canonical Feature Ordering:** Services that use machine learning models now enforce a canonical, hardcoded feature order. This eliminates bugs where predictions could be silently incorrect due to the unpredictable order of keys in a JSON payload.
    *   *Affected Services:* `proposer`, `critic`

*   **Robust Data Access:** Endpoints that process complex, nested payloads now use safe access patterns (e.g., `.get()`, checking list lengths). This prevents the services from crashing on malformed input and instead returns a helpful `400 Bad Request` error.
    *   *Affected Service:* `learner`

*   **Safe File I/O:** Services that write to the filesystem now ensure the target directory exists before attempting to write, preventing `FileNotFoundError` exceptions.
    *   *Affected Service:* `meta-controller`

*   **Resilient Orchestration:** The main orchestration loop in the `evaluator` now has a configurable timeout. This prevents the entire system from stalling if one of the downstream services hangs.
    *   *Affected Service:* `evaluator`

*   **Enhanced Observability:** The `evaluator`'s orchestration loop now increments a Prometheus counter (`evaluation_loop_timeouts_total`) when a timeout occurs, making these events easy to monitor and alert on.
    *   *Affected Service:* `evaluator`

## Phase 2: Introducing Self-Analysis Capabilities

To teach the system to identify its own problems, a new service was introduced.

### The `auditor` Service

The `auditor` is a dedicated microservice responsible for performing system-wide health checks and diagnostics. It provides a single endpoint (`/audit`) that can be used to get a real-time snapshot of the system's health.

**Current Capabilities:**
1.  **Static Asset Verification:** Checks for the existence of critical files, such as the `proposer.pkl` and `critic.pkl` models.
2.  **Live Health Probes:** Asynchronously polls the `/health` endpoint of every other microservice in the system. It can correctly distinguish between healthy, unhealthy (e.g., `503 Service Unavailable`), and unreachable (e.g., connection refused) services.

## Future Improvements & Roadmap

The following is a proposed roadmap for the continued evolution of the system.

### ☐ **Tier 1: Advanced Auditing**
-   [ ] **Configuration Audit:** The `auditor` should verify that critical environment variables are set across all services (e.g., database URLs, model paths).
-   [ ] **Schema Validation:** The `auditor` should be able to check if the data schemas used by the services (e.g., the policy file in `meta-controller`) are valid.
-   [ ] **Dissonance Monitoring:** The `auditor` should track the dissonance metric (`d`) over time and flag if it becomes consistently too high or too low, suggesting a problem with the models.

### ☐ **Tier 2: Implementing the Learning Loop**
-   [ ] **True Model Training:** Replace the placeholder `create_models.py` script with a real training pipeline that uses a proper dataset.
-   [ ] **MLflow Integration:** Integrate the `learner` service with an MLflow instance to log experiments, track model versions, and store model artifacts.
-   [ ] **Dynamic Model Loading:** The `proposer` and `critic` services should be able to dynamically load new model versions from the MLflow registry without requiring a restart.

### ☐ **Tier 3: Production Readiness**
-   [ ] **Kubernetes Deployment:** Create a Helm chart to deploy the entire system to a Kubernetes cluster.
-   [ ] **Centralized Logging:** Integrate a centralized logging solution (e.g., ELK stack or Loki) to aggregate logs from all services.
-   [ ] **Security Hardening:** Implement authentication and authorization for all endpoints.