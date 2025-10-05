from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# --- Pydantic Models for API data validation ---
class SafetyCheckInput(BaseModel):
    model_id: str
    dissonance_score: float
    # In a real system, this would include other metrics like accuracy on a golden holdout set.
    # golden_holdout_accuracy: float

class SafetyCheckOutput(BaseModel):
    decision: str # "PASS" or "FAIL"
    reason: str

# --- FastAPI Application ---
app = FastAPI(
    title="Safety Gate Service",
    description="A service that performs safety checks before allowing model updates.",
    version="0.1.0"
)

# --- Dummy Safety Gate Logic ---
# These would be configurable and much more complex in a real system.
MAX_ALLOWED_DISSONANCE = 1.5

@app.get("/")
def read_root():
    return {"message": "Welcome to the Safety Gate Service"}

@app.post("/check", response_model=SafetyCheckOutput)
def perform_safety_check(check_input: SafetyCheckInput):
    """
    Performs a safety check based on the provided metrics.
    For the POC, this is a simple rule-based check.
    """
    print("\n--- [Safety Gate] Received Safety Check Request ---")
    print(f"  - Model ID:             {check_input.model_id}")
    print(f"  - Dissonance Score:     {check_input.dissonance_score:.4f}")

    # Simple rule: Fail if dissonance is too high.
    if check_input.dissonance_score > MAX_ALLOWED_DISSONANCE:
        decision = "FAIL"
        reason = f"Dissonance score ({check_input.dissonance_score:.4f}) exceeds the maximum allowed threshold of {MAX_ALLOWED_DISSONANCE}."
        print(f"  - Decision:             {decision}")
        print(f"  - Reason:               {reason}")
        print("-----------------------------------------------------\n")
        return SafetyCheckOutput(decision=decision, reason=reason)

    # Add more checks here in the future, e.g., on golden holdout accuracy.

    decision = "PASS"
    reason = "All safety checks passed."
    print(f"  - Decision:             {decision}")
    print("-----------------------------------------------------\n")

    return SafetyCheckOutput(decision=decision, reason=reason)