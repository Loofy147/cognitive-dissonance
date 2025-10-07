# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Install system dependencies required for psycopg2 (PostgreSQL driver) and MLflow
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Install Python dependencies
# We install the full mlflow package here for the server, not the skinny client.
# Boto3 is for S3 artifact storage, and psycopg2 is for the PostgreSQL backend.
RUN pip install --no-cache-dir \
    mlflow==2.14.1 \
    boto3==1.34.140 \
    psycopg2-binary==2.9.9

# The command to run the mlflow server is specified in docker-compose.yml
# This Dockerfile just sets up the environment.