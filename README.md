# Self-Cognitive-Dissonance System — POC

This repository contains a runnable proof-of-concept of the Self-Cognitive-Dissonance System, a microservice-based architecture for model improvement. The system has been enhanced from its original placeholder state to use pre-trained machine learning models for its core logic.

It includes:
-   **Services:** `proposer`, `critic`, `evaluator`, `learner`, `meta-controller`, and `safety-gate` (all FastAPI-based).
-   **Development Environment:** A `docker-compose` setup for easy local development.
-   **Observability:** Prometheus metrics endpoints and `/health` checks for each service.
-   **Testing:** An integration test suite using `pytest`.
-   **Documentation:** A detailed architecture overview in `docs/architecture.md`.

## Architecture Overview

For a detailed explanation of the system's design, the role of each service, and the data flow between them, please see the [**Architecture Document**](./docs/architecture.md).

## Quickstart (Local)

Follow these steps to get the system running locally.

### 1. Environment Configuration

The system requires a `.env` file for configuration. Create a file named `.env` in the root of the project with the following content:

```env
# PostgreSQL Credentials
POSTGRES_USER=testuser
POSTGRES_PASSWORD=testpassword
POSTGRES_DB=testdb

# MinIO Credentials
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
```

### 2. Generate Models

The `proposer` and `critic` services use pre-trained models. Generate them by running the following script. First, ensure you have the required Python packages:

```bash
pip install -r requirements.txt
python scripts/create_models.py
```

This will create `proposer.pkl` and `critic.pkl` in the `services/models/` directory.

### 3. Build and Run the Services

Use `docker compose` to build and start all the services in the background.

```bash
# Use sudo if you encounter permission errors with the Docker daemon
sudo docker compose up -d --build
```

### 4. Watch Logs

You can tail the logs of all services to see the system in action:

```bash
sudo docker compose logs -f evaluator proposer critic learner meta-controller safety-gate
```

## Running Tests

The repository includes an integration test suite. With the services running, execute the tests using `pytest`:

```bash
pytest
```

All tests should pass, confirming that the services are running and interacting correctly.

## Next Steps

-   **Integrate MLflow:** Connect the `learner` service to an MLflow instance to track experiments and manage model versions.
-   **Enhance Learner:** Implement a true model update mechanism in the `learner` service.
-   **Deploy to Kubernetes:** Convert the `docker-compose` setup to a Helm chart for production deployment.
-   **Add Adversarial Test Cases:** Expand the test suite with more complex and adversarial scenarios.