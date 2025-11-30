# Runbooks

This document provides a set of one-page runbooks for key operational tasks.

## Runbook: Initial Kubernetes Deployment

**Objective**: To perform the first-time deployment of the application to the Kubernetes cluster.

**Prerequisites**:

*   A Kubernetes cluster is available and `kubectl` is configured to connect to it.
*   Helm is installed.
*   The application's Helm chart is available in a chart repository.

**Steps**:

1.  **Add the Helm Repository**: `helm repo add <repo-name> <repo-url>`
2.  **Create a `values.yaml` File**: Create a `values.yaml` file to override the default chart values with the production configuration (e.g., database credentials, resource limits).
3.  **Deploy the Application**: `helm install <release-name> <repo-name>/<chart-name> -f values.yaml`
4.  **Verify the Deployment**:
    *   Check the status of the pods: `kubectl get pods`
    *   Check the logs of the services: `kubectl logs -f <pod-name>`
    *   Verify that the services are accessible via their ingress endpoints.

## Runbook: Setting Up the MLflow Tracking Server

**Objective**: To set up a dedicated MLflow tracking server for experiment tracking and model management.

**Prerequisites**:

*   A PostgreSQL database is available for the MLflow backend store.
*   An S3-compatible object store (e.g., MinIO) is available for the MLflow artifact store.

**Steps**:

1.  **Deploy MLflow**: Deploy MLflow to the Kubernetes cluster using a Helm chart or a custom deployment manifest.
2.  **Configure the Backend Store**: Configure MLflow to use the PostgreSQL database as its backend store.
3.  **Configure the Artifact Store**: Configure MLflow to use the S3-compatible object store as its artifact store.
4.  **Verify the Setup**:
    *   Access the MLflow UI and verify that you can create and track experiments.
    *   Run a test script to log a model to the artifact store and verify that it appears in the UI.

## Runbook: Configuring Centralized Logging

**Objective**: To configure centralized logging for all services in the Kubernetes cluster.

**Prerequisites**:

*   An ELK stack (Elasticsearch, Logstash, Kibana) or a similar logging solution (e.g., Loki, Grafana) is deployed in the cluster.

**Steps**:

1.  **Deploy a Log Collector**: Deploy a log collector agent (e.g., Fluentd, Filebeat) to each node in the cluster.
2.  **Configure the Log Collector**: Configure the log collector to collect logs from all containers running in the cluster.
3.  **Forward Logs to the Logging Backend**: Configure the log collector to forward the logs to the logging backend (e.g., Elasticsearch, Loki).
4.  **Verify the Setup**:
    *   Access the logging UI (e.g., Kibana, Grafana) and verify that you can see logs from all services.
    *   Perform a search to find logs for a specific service or request.

## Runbook: Deploying a New Model

**Objective**: To safely deploy a new version of the `proposer` or `critic` model to production.

**Prerequisites**:

*   A new model has been trained, evaluated, and registered in the MLflow model registry.
*   The new model has been promoted to the "Production" stage in the MLflow model registry.

**Steps**:

1.  **Trigger the Deployment Pipeline**: Manually trigger the "Deploy Model" CI/CD pipeline, specifying the name and version of the model to be deployed.
2.  **Canary Deployment**: The pipeline will first deploy the new model to a single canary instance.
3.  **Monitor Performance**: Monitor the performance of the canary instance for a predefined period of time (e.g., 1 hour). Pay close attention to the following metrics:
    *   Prediction accuracy
    *   Latency
    *   Error rate
    *   Dissonance (`d`) value
4.  **Promote or Rollback**:
    *   If the performance of the canary instance is acceptable, manually approve the full rollout of the new model.
    *   If the performance of the canary instance is not acceptable, manually trigger a rollback to the previous version of the model.
5.  **Verify Deployment**: After the full rollout is complete, verify that the new model is running on all instances and that the system is stable.

## Runbook: Responding to a Security Incident

**Objective**: To effectively respond to and mitigate a security incident.

**Phases**:

1.  **Identification**:
    *   Receive an alert from the security monitoring system or a report of a potential security incident.
    *   Assemble the incident response team.
    *   Assess the severity of the incident and determine the appropriate level of response.

2.  **Containment**:
    *   Isolate the affected systems from the network.
    *   Disable any compromised user accounts.
    *   Take any other necessary steps to prevent the incident from spreading.

3.  **Eradication**:
    *   Identify and remove the root cause of the incident.
    *   Restore the affected systems from a known good backup.
    *   Apply any necessary security patches.

4.  **Recovery**:
    *   Bring the affected systems back online.
    *   Monitor the systems to ensure that they are stable and that the incident has been fully resolved.

5.  **Post-Incident Activities**:
    *   Conduct a post-mortem to identify the lessons learned from the incident.
    *   Update the incident response plan and any other relevant documentation.
    *   Implement any necessary changes to prevent similar incidents from happening in the future.
