import os

# Service URLs
PROPOSER_URL = os.getenv("PROPOSER_URL", "http://proposer:8000/predict")
CRITIC_URL = os.getenv("CRITIC_URL", "http://critic:8000/contradict")
LEARNER_URL = os.getenv("LEARNER_URL", "http://learner:8000/update")
SAFETY_URL = os.getenv("SAFETY_URL", "http://safety-gate:8000/check")
META_CONTROLLER_URL = os.getenv("META_CONTROLLER_URL", "http://meta-controller:8000/policy")

# Meta-Controller Policy
D_TARGET = float(os.getenv("D_TARGET", 0.12))
LAMBDA_MAX = float(os.getenv("LAMBDA_MAX", 0.05))
KL_EPS = float(os.getenv("KL_EPS", 0.02))
D_BUDGET_PER_HOUR = int(os.getenv("D_BUDGET_PER_HOUR", 100))
POLICY_FILE_PATH = os.getenv("POLICY_FILE_PATH", "/app/policy.json")

# Safety Gate
MAX_DISSONANCE = float(os.getenv("MAX_DISSONANCE", 0.5))

# Model Paths
PROPOSER_MODEL_PATH = os.getenv("PROPOSER_MODEL_PATH", "/app/models/proposer.pkl")
CRITIC_MODEL_PATH = os.getenv("CRITIC_MODEL_PATH", "/app/models/critic.pkl")