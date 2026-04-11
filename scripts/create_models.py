import os
import sys

import boto3
import mlflow
import mlflow.sklearn
import pandas as pd
from botocore.exceptions import ClientError
from dotenv import load_dotenv
from sklearn.neural_network import MLPClassifier

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

# Load environment variables
load_dotenv()

from services.common import config  # noqa: E402


def ensure_bucket_exists(bucket_name):
    """Creates the MinIO bucket if it does not already exist."""
    s3_client = boto3.client(
        "s3",
        endpoint_url=f"http://{os.getenv('MLFLOW_HOST', 'localhost')}:9000",
        aws_access_key_id=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
        aws_secret_access_key=os.getenv("MINIO_SECRET_KEY", "minioadmin"),
    )
    try:
        s3_client.head_bucket(Bucket=bucket_name)
        print(f"Bucket '{bucket_name}' already exists.")
    except ClientError as e:
        if e.response["Error"]["Code"] == "404":
            print(f"Bucket '{bucket_name}' not found. Creating it now.")
            s3_client.create_bucket(Bucket=bucket_name)
            print(f"Bucket '{bucket_name}' created successfully.")
        else:
            print(f"Error checking for bucket '{bucket_name}': {e}", file=sys.stderr)


def train_and_register_model(model_name, run_name, X, y):
    """Trains a model, logs it to MLflow, and sets 'production' alias."""
    print(f"Training model '{model_name}'...")
    with mlflow.start_run(run_name=run_name):
        model = MLPClassifier(
            hidden_layer_sizes=(16, 8), max_iter=1000, random_state=42
        )
        model.fit(X, y)
        model_info = mlflow.sklearn.log_model(
            sk_model=model, artifact_path="model", registered_model_name=model_name
        )

        client = mlflow.tracking.MlflowClient()
        v = model_info.registered_model_version
        client.set_registered_model_alias(
            name=model_name,
            alias="production",
            version=v,
        )
        print(f"Promoted version {v} of '{model_name}' to production.")


if __name__ == "__main__":
    mlflow.set_tracking_uri(config.MLFLOW_TRACKING_URI)

    for task_id, task_cfg in config.TASKS.items():
        print(f"\n--- Initial Training for Task: {task_id} ---")
        try:
            df = pd.read_csv(os.path.join(project_root, task_cfg["dataset_path"]))
            target_col = df.columns[-1]
            X = df[task_cfg["feature_names"]]
            y = df[target_col]

            # Simple binarization of target if needed (regression to classification)
            if y.dtype == "float64" and len(y.unique()) > 10:
                y = (y > y.median()).astype(int)

            train_and_register_model(
                task_cfg["proposer_model_name"], f"{task_id}-proposer", X, y
            )
            train_and_register_model(
                task_cfg["critic_model_name"], f"{task_id}-critic", X, y
            )
        except Exception as e:
            print(f"Skipping task '{task_id}' initial training: {e}")
