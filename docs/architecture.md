# System Architecture: Self-Cognitive-Dissonance System

This document provides a detailed overview of the system's architecture, the role of each microservice, and the data flow between them.

## 1. Overview

The Self-Cognitive-Dissonance System is a microservices-based architecture designed to simulate a cognitive dissonance loop for machine learning model improvement. The core idea is to have a `proposer` model that makes predictions, a `critic` model that challenges those predictions, and a `learner` that uses the resulting "dissonance" to improve the models over time.

The system is composed of several independent services that communicate via synchronous HTTP requests. It uses a centralized **MLflow Model Registry** for model management, ensuring that services can dynamically load the latest production-ready models.

## 2. Service Breakdown

The system consists of the following microservices:

-   **Evaluator:** The central orchestrator of the system.
-   **Proposer:** Generates an initial prediction using a model from the MLflow Model Registry.
-   **Critic:** Generates a "contradictory" prediction using its own model from the MLflow Model Registry.
-   **Learner:** Calculates the loss (dissonance) and logs experiment results to MLflow.
-   **Safety Gate:** A rule-based system that can block a learning cycle.
-   **Meta-Controller:** Manages the system's operational policy.

### 2.1. Proposer

The `proposer` service is responsible for making the initial prediction.

-   **Endpoint:** `/predict`
-   **Functionality:**
    -   At startup, it loads the latest "production" version of its **MLP neural network** model from the **MLflow Model Registry**.
    -   Accepts an `input_id` and a dictionary of `features`.
    -   Uses the loaded model to generate a probability distribution over two classes (A and B).
    -   Returns the prediction along with the model's run ID as the version.

### 2.2. Critic

The `critic` service challenges the `proposer`'s prediction.

-   **Endpoint:** `/contradict`
-   **Functionality:**
    -   At startup, it loads the latest "production" version of its own **MLP neural network** model from the **MLflow Model Registry**.
    -   Accepts the proposer's output and the original `features`.
    -   Generates its own "contradictory" prediction.
    -   Calculates a dissonance score (`d`), which is the absolute difference between the two predictions.
    -   Returns its prediction and the dissonance score.

### 2.3. Learner

The `learner` service is responsible for processing the outcome of the dissonance loop.

-   **Endpoint:** `/update`
-   **Functionality:**
    -   Accepts the full context: the `proposal`, the `contradiction`, and the `features`.
    -   Calculates a loss value based on the dissonance.
    -   Logs experiment parameters and metrics (like the loss) to the **MLflow Tracking Server**.

*The remaining service descriptions (`Evaluator`, `Safety Gate`, `Meta-Controller`) are unchanged.*

## 3. Data Flow Diagram

The data flow for a single `run_once` iteration is as follows, now including the MLflow integration:

```
+----------------------+      +------------------+
| MLflow Model Registry|      |   [Proposer]     |
| (Serves Models)      |<-----| (Loads Model)    |
+----------------------+      +------------------+
        ^                           |
        |                           | (prediction)
+----------------------+      +------------------+
| MLflow Model Registry|      |     [Critic]     |
| (Serves Models)      |<-----| (Loads Model)    |
+----------------------+      +------------------+
                                    |
                                    | (contradiction)
                                    v
[Evaluator] -> [Proposer] -> [Critic] -> [Safety Gate] -> [Learner]
                                                            |
                                                            | (Logs Metrics)
                                                            v
                                                  +----------------------+
                                                  | MLflow Tracking Server|
                                                  +----------------------+
```

## 4. Configuration

All services are configured via environment variables, which are documented in `services/common/config.py` and injected via `docker-compose.yml`. This allows for easy management of service URLs, MLflow URIs, and policy parameters.
