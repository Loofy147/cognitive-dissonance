import os

# Service URLs
PROPOSER_URL = os.getenv("PROPOSER_URL", "http://proposer:8000/predict")
CRITIC_URL = os.getenv("CRITIC_URL", "http://critic:8000/contradict")
LEARNER_URL = os.getenv("LEARNER_URL", "http://learner:8000/update")
SAFETY_URL = os.getenv("SAFETY_URL", "http://safety-gate:8000/check")
META_CONTROLLER_URL = os.getenv(
    "META_CONTROLLER_URL", "http://meta-controller:8000/policy"
)

# Meta-Controller Policy
D_TARGET = float(os.getenv("D_TARGET", 0.12))
LAMBDA_MAX = float(os.getenv("LAMBDA_MAX", 0.05))
KL_EPS = float(os.getenv("KL_EPS", 0.02))
D_BUDGET_PER_HOUR = int(os.getenv("D_BUDGET_PER_HOUR", 100))
POLICY_FILE_PATH = os.getenv("POLICY_FILE_PATH", "/app/policy.json")

# Safety Gate
MAX_DISSONANCE = float(os.getenv("MAX_DISSONANCE", 0.5))

# Evaluator
EVALUATOR_LOOP_TIMEOUT_SECONDS = float(
    os.getenv("EVALUATOR_LOOP_TIMEOUT_SECONDS", 30.0)
)

# Health check URLs for the auditor
HEALTH_CHECK_URLS = {
    "proposer": "http://proposer:8000/health",
    "critic": "http://critic:8000/health",
    "evaluator": "http://evaluator:8000/health",
    "learner": "http://learner:8000/health",
    "meta-controller": "http://meta-controller:8000/health",
    "safety-gate": "http://safety-gate:8000/health",
}

# Configuration check URLs for the auditor
CONFIG_URLS = {
    "proposer": "http://proposer:8000/config",
    "critic": "http://critic:8000/config",
    "evaluator": "http://evaluator:8000/config",
    "learner": "http://learner:8000/config",
    "meta-controller": "http://meta-controller:8000/config",
    "safety-gate": "http://safety-gate:8000/config",
}

# MLflow Configuration
MLFLOW_HOST = os.getenv("MLFLOW_HOST", "mlflow")
MLFLOW_TRACKING_URI = f"http://{MLFLOW_HOST}:5000"

# Multi-Task Configuration
TASKS = {
    "diabetes": {
        "feature_names": [
            "age",
            "gender",
            "polyuria",
            "polydipsia",
            "sudden_weight_loss",
            "weakness",
            "polyphagia",
            "genital_thrush",
            "visual_blurring",
            "itching",
            "irritability",
            "delayed_healing",
            "partial_paresis",
            "muscle_stiffness",
            "alopecia",
            "obesity",
        ],
        "proposer_model_name": "proposer-diabetes",
        "critic_model_name": "critic-diabetes",
        "dataset_path": "data/diabetes/diabetes_data.csv",
    },
    "heart_failure": {
        "feature_names": [
            "Age",
            "Sex",
            "ChestPainType",
            "RestingBP",
            "Cholesterol",
            "FastingBS",
            "RestingECG",
            "MaxHR",
            "ExerciseAngina",
            "Oldpeak",
            "ST_Slope",
        ],
        "proposer_model_name": "proposer-heart_failure",
        "critic_model_name": "critic-heart_failure",
        "dataset_path": "data/heart_failure/heart_failure_data.csv",
    },
    "breast_cancer": {
        "feature_names": [
            "radius_mean",
            "texture_mean",
            "perimeter_mean",
            "area_mean",
            "smoothness_mean",
            "compactness_mean",
            "concavity_mean",
            "concave points_mean",
            "symmetry_mean",
            "fractal_dimension_mean",
        ],
        "proposer_model_name": "proposer-breast_cancer",
        "critic_model_name": "critic-breast_cancer",
        "dataset_path": "data/breast_cancer/breast_cancer_data.csv",
    },

    "nemotron_reasoning": {
        "feature_names": ["prompt"],
        "proposer_model_name": "proposer-nemotron",
        "critic_model_name": "critic-nemotron",
        "dataset_path": "data/nemotron/train.csv",
    },
}

DEFAULT_TASK = os.getenv("DEFAULT_TASK", "diabetes")


# Helper to get task config safely
def get_task_config(task_id: str):
    return TASKS.get(task_id, TASKS[DEFAULT_TASK])


# (Legacy) Keeping these for backward compatibility
FEATURE_NAMES = get_task_config(DEFAULT_TASK)["feature_names"]
PROPOSER_MODEL_NAME = get_task_config(DEFAULT_TASK)["proposer_model_name"]
CRITIC_MODEL_NAME = get_task_config(DEFAULT_TASK)["critic_model_name"]
