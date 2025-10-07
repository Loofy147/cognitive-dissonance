# System Architecture: Self-Cognitive-Dissonance System

This document provides a detailed overview of the system's architecture, the role of each microservice, and the data flow between them.

## 1. Overview

The Self-Cognitive-Dissonance System is a microservices-based architecture designed to simulate a cognitive dissonance loop for machine learning model improvement. The core idea is to have a `proposer` model that makes predictions, a `critic` model that challenges those predictions, and a `learner` that uses the resulting "dissonance" to improve the models over time.

The system is composed of several independent services that communicate via synchronous HTTP requests. This design allows for scalability, resilience, and independent development of each component.

## 2. Service Breakdown

The system consists of the following microservices:

-   **Evaluator:** The central orchestrator of the system. It drives the main cognitive dissonance loop.
-   **Proposer:** Generates an initial prediction based on input features.
-   **Critic:** Generates a "contradictory" prediction to challenge the proposer.
-   **Learner:** Calculates the loss (dissonance) and would, in a full implementation, update the models.
-   **Safety Gate:** A rule-based system that can block a learning cycle if the dissonance is too high.
-   **Meta-Controller:** Manages the system's operational policy, such as dissonance targets and safety thresholds.

### 2.1. Evaluator

The `evaluator` service is the heart of the system. Its primary responsibility is to orchestrate the cognitive dissonance loop.

-   **Endpoint:** `/run_once`, `/start_loop`
-   **Workflow:**
    1.  Generates a set of input features.
    2.  Calls the `proposer` to get an initial prediction.
    3.  Calls the `critic`, providing both the original features and the proposer's prediction.
    4.  Calls the `safety_gate` to check if the contradiction from the critic is within acceptable bounds.
    5.  If the check passes, it calls the `learner` with the full context (proposal, contradiction, and features).
    6.  The `/start_loop` endpoint uses `BackgroundTasks` to run this loop continuously.

### 2.2. Proposer

The `proposer` service is responsible for making the initial prediction.

-   **Endpoint:** `/predict`
-   **Functionality:**
    -   Loads a pre-trained **MLP (Multi-layer Perceptron) neural network** model (`proposer.pkl`) at startup. This model is trained on a non-linear "two moons" dataset to handle complex patterns.
    -   Accepts an `input_id` and a dictionary of `features`.
    -   Uses the model to generate a probability distribution over two classes (A and B).
    -   Returns the prediction along with a model version.

### 2.3. Critic

The `critic` service challenges the `proposer`'s prediction.

-   **Endpoint:** `/contradict`
-   **Functionality:**
    -   Loads its own pre-trained **MLP neural network** model (`critic.pkl`), which has a different architecture from the proposer's to ensure cognitive dissonance.
    -   Accepts the proposer's output along with the original `features`.
    -   Generates its own "contradictory" prediction based on the features.
    -   Calculates a dissonance score (`d`), which is the absolute difference between the proposer's and its own prediction.
    -   Returns its prediction and the dissonance score.

### 2.4. Learner

The `learner` service is responsible for processing the outcome of the dissonance loop.

-   **Endpoint:** `/update`
-   **Functionality:**
    -   Accepts the full context: the `proposal`, the `contradiction`, and the `features`.
    -   Calculates a loss value based on the dissonance.
    -   In a production system, this service would be responsible for triggering model retraining or updates (e.g., via MLflow). In this POC, it simply logs the loss and features.

### 2.5. Safety Gate

The `safety_gate` provides a simple, rule-based check to prevent unstable learning.

-   **Endpoint:** `/check`
-   **Functionality:**
    -   Accepts the output from the `critic`.
    -   Checks if the dissonance score (`d`) exceeds a configured threshold (`MAX_DISSONANCE`).
    -   Returns `{'allow': False}` if the threshold is exceeded, blocking the learning cycle.

### 2.6. Meta-Controller

The `meta_controller` manages the high-level policy for the entire system.

-   **Endpoint:** `/policy`
-   **Functionality:**
    -   Persists its policy to a JSON file (`policy.json`).
    -   Provides the current policy to other services.
    -   Allows the policy to be updated via a POST request.
    -   Manages parameters like dissonance targets, learning rates, and safety thresholds.

## 3. Data Flow Diagram

The data flow for a single `run_once` iteration is as follows:

```
[Evaluator] --(features)--> [Proposer]
      |
      <--(proposal)--
      |
      +--(proposal, features)--> [Critic]
      |
      <--(contradiction, d)--
      |
      +--(contradiction, d)--> [Safety Gate]
      |
      <--(allow/deny)--
      |
      (if allow) --(proposal, contradiction, features)--> [Learner]
      |
      <--(update status)--
```

## 4. Configuration

All services are configured via environment variables, which are documented in `services/common/config.py` and injected via `docker-compose.yml`. This allows for easy management of service URLs, model paths, and policy parameters. The `meta-controller`'s policy is also persisted to a file on a mounted volume for durability.