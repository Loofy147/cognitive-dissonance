from fastapi import FastAPI
from pydantic import BaseModel
import numpy as np

# --- Pydantic Models for API data validation ---
class PredictionInput(BaseModel):
    # In a real system, these would be the actual features your model expects.
    feature1: float
    feature2: float

class PredictionOutput(BaseModel):
    model_id: str
    prediction: list[float]

# --- FastAPI Application ---
app = FastAPI(
    title="Proposer Service",
    description="A service that wraps a machine learning model to provide predictions.",
    version="0.1.0"
)

# --- Dummy Model ---
# In a real system, you would load a trained model file here (e.g., pickle, ONNX)
class ProposerModel:
    def __init__(self, model_id="base_model_v1"):
        self.model_id = model_id
        print(f"[{self.model_id}] Proposer model loaded.")

    def predict(self, input_data: PredictionInput) -> np.ndarray:
        """
        Simulates a prediction based on the input data.
        """
        print(f"[{self.model_id}] Received input: {input_data.dict()}")
        # A dummy logic: prediction changes slightly based on input
        base_prediction = np.array([0.75, 0.25])
        # A simple way to make the output dependent on the input for the POC
        modifier = (input_data.feature1 - input_data.feature2) / 10.0
        prediction = base_prediction + np.array([modifier, -modifier])
        # Ensure probabilities sum to 1
        prediction = np.clip(prediction, 0, 1)
        prediction /= np.sum(prediction)

        print(f"[{self.model_id}] Generated prediction: {prediction.tolist()}")
        return prediction

model = ProposerModel()

@app.get("/")
def read_root():
    return {"message": f"Welcome to the Proposer Service: {model.model_id}"}

@app.post("/predict", response_model=PredictionOutput)
def predict(input_data: PredictionInput):
    """
    Takes input features and returns a model prediction.
    """
    prediction_array = model.predict(input_data)
    return PredictionOutput(
        model_id=model.model_id,
        prediction=prediction_array.tolist()
    )