# Self-Cognitive-Dissonance System — POC

This repository contains a runnable proof-of-concept of the Self-Cognitive-Dissonance System, a microservice-based architecture for model improvement. The system has been enhanced to use **MLP (Multi-layer Perceptron) neural networks** for its core logic and now integrates with **MLflow** for robust model lifecycle management.

It includes:
-   **Services:** `proposer`, `critic`, `evaluator`, `learner`, `meta-controller`, and `safety-gate` (all FastAPI-based).
-   **MLOps:** An MLflow server for experiment tracking and a centralized Model Registry.
-   **Development Environment:** A `docker-compose` setup for easy local development.
-   **Observability:** Prometheus metrics endpoints and `/health` checks for each service.
-   **Testing:** An integration test suite using `pytest`.
-   **Documentation:** A detailed architecture overview in `docs/architecture.md`.

## Architecture Overview

For a detailed explanation of the system's design, the role of each service, and the data flow between them, please see the [**Architecture Document**](./docs/architecture.md).

## Quickstart (Local)

Follow these steps to get the system running locally.

### 1. Environment Configuration

The system requires a `.env` file for configuration. Create one by copying the example file:

```bash
cp .env.example .env
```

The default values in `.env.example` are suitable for local development.

### 2. Install Dependencies

Install the required Python packages using pip:

```bash
pip install -r requirements.txt
```

### 3. Build and Run the Services

Use `docker compose` to build and start all the services (including the MLflow server) in the background.

```bash
# Use sudo if you encounter permission errors with the Docker daemon
sudo docker compose up --build -d
```

### 4. Train and Register Models

The `proposer` and `critic` services now load their models from the MLflow Model Registry. Run the following script to train the models and register them with the MLflow server:

```bash
MLFLOW_HOST=localhost python scripts/create_models.py
```

This script connects to the MLflow server running in Docker, trains the models, and assigns them the `"production"` alias so they can be served.

### 5. Watch Logs (Optional)

You can tail the logs of all services to see the system in action:

```bash
sudo docker compose logs -f evaluator proposer critic learner meta-controller safety-gate
```

## Running Tests

The repository includes an integration test suite. With the services running, execute the tests using `pytest`:

```bash
pytest
```

## Next Steps

-   [x] **Integrate MLflow:** Connect the services to an MLflow instance to track experiments and manage model versions.
-   [ ] **Enhance Learner:** Implement a true model update mechanism in the `learner` service.
-   [ ] **Deploy to Kubernetes:** Convert the `docker-compose` setup to a Helm chart for production deployment.
-   [ ] **Add Adversarial Test Cases:** Expand the test suite with more complex and adversarial scenarios.
