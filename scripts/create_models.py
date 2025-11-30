import mlflow
import mlflow.sklearn
import numpy as np
from sklearn.neural_network import MLPClassifier
from sklearn.datasets import make_moons
import os
import sys
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

# Load environment variables from .env file
load_dotenv()

from services.common import config

def ensure_bucket_exists(bucket_name):
    """Creates the MinIO bucket if it does not already exist."""
    s3_client = boto3.client(
        's3',
        endpoint_url=f"http://{os.getenv('MLFLOW_HOST', 'localhost')}:9000",
        aws_access_key_id=os.getenv("MINIO_ACCESS_KEY"),
        aws_secret_access_key=os.getenv("MINIO_SECRET_KEY")
    )
    try:
        s3_client.head_bucket(Bucket=bucket_name)
        print(f"Bucket '{bucket_name}' already exists.")
    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            print(f"Bucket '{bucket_name}' not found. Creating it now.")
            s3_client.create_bucket(Bucket=bucket_name)
            print(f"Bucket '{bucket_name}' created successfully.")
        else:
            print(f"Error checking for bucket '{bucket_name}': {e}", file=sys.stderr)
            sys.exit(1)

def train_and_register_model(model_name, run_name, hidden_layer_sizes, activation, solver, alpha):
    """
    Trains a model, logs it to MLflow, registers it, and sets the 'production' alias.
    """
    print(f"Starting MLflow run '{run_name}' for model '{model_name}'...")
    with mlflow.start_run(run_name=run_name) as run:
        X, y = make_moons(n_samples=200, noise=0.2, random_state=42)
        params = {
            "hidden_layer_sizes": str(hidden_layer_sizes), "activation": activation,
            "solver": solver, "alpha": alpha, "max_iter": 1000,
        }
        mlflow.log_params(params)
        print(f"Logged parameters: {params}")
        model = MLPClassifier(
            hidden_layer_sizes=hidden_layer_sizes, activation=activation, solver=solver,
            alpha=alpha, random_state=1, max_iter=1000,
        )
        model.fit(X, y)
        model_info = mlflow.sklearn.log_model(
            sk_model=model, artifact_path="model", registered_model_name=model_name,
        )
        print(f"Logged and registered model '{model_name}' to MLflow.")

        client = mlflow.tracking.MlflowClient()
        client.set_registered_model_alias(
            name=model_name,
            alias="production",
            version=model_info.registered_model_version
        )
        print(f"Set 'production' alias for version {model_info.registered_model_version} of model '{model_name}'.")

        print(f"MLflow run '{run_name}' completed with run_id: {run.info.run_id}")

if __name__ == "__main__":
    os.environ["AWS_ACCESS_KEY_ID"] = os.getenv("MINIO_ACCESS_KEY")
    os.environ["AWS_SECRET_ACCESS_KEY"] = os.getenv("MINIO_SECRET_KEY")
    os.environ["MLFLOW_S3_ENDPOINT_URL"] = f"http://{os.getenv('MLFLOW_HOST', 'localhost')}:9000"

    print("Ensuring MinIO bucket exists for MLflow artifacts...")
    ensure_bucket_exists("mlflow")

    print("Generating new MLP models and registering them with MLflow...")
    tracking_uri = config.MLFLOW_TRACKING_URI
    print(f"Setting MLflow tracking URI to: {tracking_uri}")
    mlflow.set_tracking_uri(tracking_uri)

    try:
        mlflow.get_tracking_uri()
        print("Successfully connected to the MLflow tracking server.")
    except Exception as e:
        print(f"Could not connect to MLflow server at {tracking_uri}", file=sys.stderr)
        sys.exit(1)

    train_and_register_model(
        model_name="proposer-model", run_name="proposer-training-run",
        hidden_layer_sizes=(10, 5), activation='relu', solver='adam', alpha=1e-5
    )
    train_and_register_model(
        model_name="critic-model", run_name="critic-training-run",
        hidden_layer_sizes=(5, 10, 5), activation='tanh', solver='adam', alpha=1e-4
    )
    print("\nBoth MLP models have been trained, registered, and assigned the 'production' alias in MLflow.")
