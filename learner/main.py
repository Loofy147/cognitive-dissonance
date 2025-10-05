from fastapi import FastAPI
from pydantic import BaseModel

# --- Pydantic Models for API data validation ---
class UpdateInfo(BaseModel):
    model_id: str
    dissonance_score: float
    message: str

# --- FastAPI Application ---
app = FastAPI(
    title="Learner Service",
    description="A service responsible for updating models based on evaluation results.",
    version="0.1.0"
)

@app.get("/")
def read_root():
    return {"message": "Welcome to the Learner Service"}

@app.post("/update")
def trigger_update(update_info: UpdateInfo):
    """
    Receives information from the evaluator and triggers a model update process.
    For the POC, this will just log the information.
    """
    print("\n--- [Learner] Received Model Update Trigger ---")
    print(f"  - Model to update:    {update_info.model_id}")
    print(f"  - Dissonance Score:   {update_info.dissonance_score:.4f}")
    print(f"  - Message:            {update_info.message}")
    print("  - Status:             (POC: Logging only, no real update performed)")
    print("--------------------------------------------------\n")

    return {
        "status": "Update process acknowledged",
        "details": update_info.dict()
    }