# Self-Cognitive-Dissonance System — POC

This repository contains a runnable POC of the Self-Cognitive-Dissonance System (multi-service). It includes:
- proposer, critic, evaluator, learner, meta-controller, safety-gate services (FastAPI)
- docker-compose for local development
- Prometheus metrics endpoints, health/readiness
- MLflow + MinIO compose for model artifact management (optional)
- Helm skeleton for K8s productionization
- GitHub Actions CI: lint, tests, build

## Quickstart (local)
1. Copy `.env.example` to `.env` and edit if needed.
2. Build & run:

```bash
docker-compose build --pull
docker-compose up --build

3. Watch logs:



docker-compose logs -f evaluator proposer critic learner meta-controller safety-gate

Running tests

pytest -q

Next steps

Integrate MLflow and MinIO for model lifecycle (see mlops/)

Convert compose to Helm & deploy to Kubernetes

Add additional Red-team adversarial testcases