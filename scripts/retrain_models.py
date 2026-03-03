import json
import os
import sys

import mlflow
import mlflow.sklearn
import pandas as pd
import psycopg2
from dotenv import load_dotenv
from sklearn.neural_network import MLPClassifier

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

# Load environment variables
load_dotenv()

from services.common import config  # noqa: E402  # noqa: E402  # noqa: E402


def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        database=os.getenv("POSTGRES_DB", "cd_meta"),
        user=os.getenv("POSTGRES_USER", "cd_user"),
        password=os.getenv("POSTGRES_PASSWORD", "cd_pass"),
    )


def retrain_task(task_id):
    """
    Pulls dissonant samples for a task, combines with original data, and trains a new model.
    """
    print(f"\n--- Retraining Loop for Task: {task_id} ---")
    task_cfg = config.get_task_config(task_id)

    # 1. Load original data
    original_df = pd.read_csv(os.path.join(project_root, task_cfg["dataset_path"]))
    target_col = original_df.columns[-1]

    # 2. Fetch dissonant samples from DB
    try:
        conn = get_db_connection()
        query = "SELECT features, contradiction->'contradictory'->0->'p' as label FROM dissonant_samples WHERE task_id = %s"
        dissonant_df = pd.read_sql(query, conn, params=(task_id,))
        conn.close()
    except Exception as e:
        print(f"Error fetching from DB: {e}")
        dissonant_df = pd.DataFrame()

    if not dissonant_df.empty:
        print(f"Found {len(dissonant_df)} dissonant samples to learn from.")

        # Parse JSON features and flatten
        features_list = [
            json.loads(f) if isinstance(f, str) else f for f in dissonant_df["features"]
        ]
        d_features_df = pd.DataFrame(features_list)

        # For simplicity, we use the critic's prediction as the 'silver' label for re-training
        # in a real system we'd use ground truth or a more complex meta-learner.
        d_features_df[target_col] = (dissonant_df["label"] > 0.5).astype(int)

        # Combine
        combined_df = pd.concat([original_df, d_features_df], ignore_index=True)
    else:
        print("No dissonant samples found. Training on original data only.")
        combined_df = original_df

    X = combined_df[task_cfg["feature_names"]]
    y = combined_df[target_col]

    # 3. MLflow Training
    mlflow.set_tracking_uri(config.MLFLOW_TRACKING_URI)

    for model_type in ["proposer", "critic"]:
        model_name = task_cfg[f"{model_type}_model_name"]
        run_name = f"retrain-{model_type}-{task_id}"

        with mlflow.start_run(run_name=run_name):
            print(f"Training {model_type} model...")

            # Simple hyperparam search or just re-training
            model = MLPClassifier(
                hidden_layer_sizes=(16, 16), max_iter=1000, random_state=42
            )
            model.fit(X, y)

            model_info = mlflow.sklearn.log_model(
                sk_model=model, artifact_path="model", registered_model_name=model_name
            )

            # 4. Promotion (Always promote in this POC)
            client = mlflow.tracking.MlflowClient()
            client.set_registered_model_alias(
                name=model_name,
                alias="production",
                version=model_info.registered_model_version,
            )
            print(
                f"Promoted {model_name} version {model_info.registered_model_version} to production."
            )


if __name__ == "__main__":
    # Ensure S3 endpoint is set for MinIO
    os.environ["MLFLOW_S3_ENDPOINT_URL"] = (
        f"http://{os.getenv('MLFLOW_HOST', 'localhost')}:9000"
    )
    os.environ["AWS_ACCESS_KEY_ID"] = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    os.environ["AWS_SECRET_ACCESS_KEY"] = os.getenv("MINIO_SECRET_KEY", "minioadmin")

    for task_id in config.TASKS.keys():
        retrain_task(task_id)
