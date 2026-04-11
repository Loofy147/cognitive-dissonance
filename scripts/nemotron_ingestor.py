import os
import sys
import pandas as pd

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

def ingest_nemotron():
    print("Ingesting Nemotron dataset...")
    data_path = os.path.join(project_root, "data", "nemotron")
    train_path = os.path.join(data_path, "train.csv")

    if not os.path.exists(train_path):
        print(f"Error: {train_path} not found.")
        return

    df = pd.read_csv(train_path)
    print(f"Loaded {len(df)} samples from train.csv")

    # In a real scenario, we might want to do some specific preprocessing
    # such as extracting the 'boxed' answers or categorizing by puzzle type.
    # For now, we ensure it is accessible to the system.

    print("Nemotron ingestion complete.")

if __name__ == "__main__":
    ingest_nemotron()
