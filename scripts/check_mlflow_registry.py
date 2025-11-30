import os
import sys
from dotenv import load_dotenv
import mlflow

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)
load_dotenv()

from services.common import config

def inspect_model_registry():
    """
    Connects to the MLflow server and prints the details of all registered models.
    """
    try:
        client = mlflow.tracking.MlflowClient()
        print("Successfully connected to MLflow server.")

        registered_models = client.search_registered_models()

        if not registered_models:
            print("\nNo registered models found in the registry.")
            return

        print("\n--- Inspecting MLflow Model Registry ---")
        for model in registered_models:
            print(f"\nModel: '{model.name}'")
            print("-" * 20)
            if model.latest_versions:
                for version in model.latest_versions:
                    print(f"  Version: {version.version}")
                    print(f"    Stage: {version.current_stage}")
                    print(f"    Run ID: {version.run_id}")
                    print(f"    Aliases: {version.aliases}")
            else:
                print("  No versions found for this model.")
        print("\n--- Inspection Complete ---")

    except Exception as e:
        print(f"An error occurred while inspecting the model registry: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    # Set credentials and endpoint URL for MinIO/S3
    os.environ["AWS_ACCESS_KEY_ID"] = os.getenv("MINIO_ACCESS_KEY")
    os.environ["AWS_SECRET_ACCESS_KEY"] = os.getenv("MINIO_SECRET_KEY")
    os.environ["MLFLOW_S3_ENDPOINT_URL"] = f"http://{os.getenv('MLFLOW_HOST', 'localhost')}:9000"

    # Set the MLflow tracking URI
    mlflow.set_tracking_uri(config.MLFLOW_TRACKING_URI)

    inspect_model_registry()
