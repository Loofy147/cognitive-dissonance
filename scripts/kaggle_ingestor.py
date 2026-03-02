import json
import os
import sys

import pandas as pd
from kaggle.api.kaggle_api_extended import KaggleApi

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from services.common import config  # noqa: E402  # noqa: E402


def ingest_dataset(dataset_ref, task_id, sep=","):
    """
    Downloads a Kaggle dataset, preprocesses it, and adds it to the system TASKS.
    """
    print(f"Ingesting dataset '{dataset_ref}' as task '{task_id}'...")

    api = KaggleApi()
    api.authenticate()

    # Download dataset
    download_path = os.path.join(project_root, "data", task_id)
    os.makedirs(download_path, exist_ok=True)
    api.dataset_download_files(dataset_ref, path=download_path, unzip=True)

    # Find the CSV file
    csv_files = [f for f in os.listdir(download_path) if f.endswith(".csv")]
    if not csv_files:
        print(f"Error: No CSV file found in {download_path}")
        return

    csv_path = os.path.join(download_path, csv_files[0])
    df = pd.read_csv(csv_path, sep=sep)

    # Basic cleaning: drop columns with too many NaNs
    df = df.dropna(axis=1, thresh=len(df) * 0.5)
    df = df.dropna()

    # Assume the last column is the target for classification
    target_col = df.columns[-1]
    feature_cols = [c for c in df.columns if c != target_col]

    # Simple encoding for object columns
    for col in feature_cols:
        if df[col].dtype == "object":
            df[col] = df[col].astype("category").cat.codes

    # Save the cleaned dataset
    cleaned_path = os.path.join(download_path, f"{task_id}_data.csv")
    df.to_csv(cleaned_path, index=False)

    print(f"Successfully ingested and cleaned dataset for task '{task_id}'.")
    print(f"Features: {feature_cols}")
    print(f"Target: {target_col}")

    # Update config.py (appending new task to TASKS dict)
    # This is a bit hacky, normally we'd have a dynamic config service or DB,
    # but for this POC we'll append to the config file.

    task_entry = {
        "feature_names": feature_cols,
        "proposer_model_name": f"proposer-{task_id}",
        "critic_model_name": f"critic-{task_id}",
        "dataset_path": f"data/{task_id}/{task_id}_data.csv",
    }

    print("\nAdd this entry to services/common/config.py TASKS:")
    print(f'    "{task_id}": {json.dumps(task_entry, indent=8)},')


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python scripts/kaggle_ingestor.py <dataset_ref> <task_id> [sep]")
        sys.exit(1)

    dataset_ref = sys.argv[1]
    task_id = sys.argv[2]
    sep = sys.argv[3] if len(sys.argv) > 3 else ","

    ingest_dataset(dataset_ref, task_id, sep)
