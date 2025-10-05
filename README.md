# Self-Cognitive Dissonance System

This repository contains the source code for a "Self-Cognitive Dissonance System," an MLOps platform designed to improve the robustness and reliability of machine learning models through controlled, internal conflict.

## Overview

The system is built around the concept of "dissonance," where a pool of "Proposer" models generates predictions, and a "Critic" component challenges these proposals by creating contradictory scenarios. An "Evaluator" measures the level of dissonance, and a "Meta-Controller" uses this signal to guide the learning process, ensuring that the models improve without compromising production safety.

This project is structured as a collection of microservices and components managed via Docker Compose for local development and designed for deployment on Kubernetes in production.

## Project Structure

- `services/`: Contains the core API services, including the `meta-controller`.
- `models/`: Contains the "Proposer" models and their training/inference scripts.
- `critic/`: Contains the logic for the "Critic" or contradiction generator.
- `evaluator/`: Contains the sandbox environment for evaluating dissonance.
- `infra/`: Holds infrastructure-as-code, such as `docker-compose.yml` and Kubernetes manifests.
- `mlops/`: Tooling for model and data versioning, tracking, and drift detection (e.g., MLflow).
- `tests/`: Unit, integration, and end-to-end tests.
- `docs/`: Project documentation, including Architecture Decision Records (ADRs).

## Getting Started (Local Development)

### Prerequisites

- Docker
- Docker Compose

### Running the System

1.  **Build and start the services:**
    ```bash
    docker-compose -f infra/docker-compose.yml build
    docker-compose -f infra/docker-compose.yml up
    ```

2.  **Interact with the Meta-Controller API:**
    - The API will be available at `http://localhost:8000`.
    - You can view the OpenAPI documentation at `http://localhost:8000/docs`.

3.  **Check the logs:**
    ```bash
    docker-compose -f infra/docker-compose.yml logs -f <service_name>
    ```
    (e.g., `meta-controller`, `proposer`, `critic`)

## High-Level Architecture

The system consists of the following key components:

- **Meta-Controller:** The central brain, managing policies and deployment strategies.
- **Proposer Pool:** A set of diverse ML models making predictions.
- **Critic Generator:** Creates challenges and counterfactuals.
- **Evaluator Sandbox:** A safe environment to measure performance and dissonance.
- **Experience Store:** A database and object store for logging all events, models, and data.
- **Safety Gate:** A set of automated rules to prevent harmful model updates.

For more details, refer to the architecture documents in the `docs/` directory.