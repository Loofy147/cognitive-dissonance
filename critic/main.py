from fastapi import FastAPI
from pydantic import BaseModel
import numpy as np

# --- Pydantic Models for API data validation ---
class ContradictionInput(BaseModel):
    model_id: str
    prediction: list[float]

class ContradictionOutput(BaseModel):
    critic_id: str
    contradiction: list[float]

# --- FastAPI Application ---
app = FastAPI(
    title="Critic Service",
    description="A service that generates contradictions to challenge model predictions.",
    version="0.1.0"
)

# --- Dummy Critic Logic ---
class CriticModel:
    def __init__(self, critic_id="contradictor_v1"):
        self.critic_id = critic_id
        print(f"[{self.critic_id}] Critic model loaded.")

    def generate_contradiction(self, input_data: ContradictionInput) -> np.ndarray:
        """
        Generates a "contradictory" scenario or example.
        """
        print(f"[{self.critic_id}] Received proposal prediction: {input_data.prediction}")

        # Simple contradiction logic for the POC: invert the probabilities.
        # This simulates finding a scenario where the opposite outcome is likely.
        contradiction = 1.0 - np.array(input_data.prediction)

        print(f"[{self.critic_id}] Generated contradiction: {contradiction.tolist()}")
        return contradiction

model = CriticModel()

@app.get("/")
def read_root():
    return {"message": f"Welcome to the Critic Service: {model.critic_id}"}

@app.post("/generate_contradiction", response_model=ContradictionOutput)
def generate_contradiction(input_data: ContradictionInput):
    """
    Takes a model prediction and returns a generated contradiction.
    """
    contradiction_array = model.generate_contradiction(input_data)
    return ContradictionOutput(
        critic_id=model.critic_id,
        contradiction=contradiction_array.tolist()
    )