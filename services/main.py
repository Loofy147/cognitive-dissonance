from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

import models
from database import SessionLocal, engine, get_db

# Create the database tables if they don't exist
models.Base.metadata.create_all(bind=engine)

# --- Pydantic Models for API data validation ---
# This model is used for request bodies
class PolicyUpdate(BaseModel):
    lambda_val: float
    d_target: float

# This model is used for responses, including the ID
class PolicyResponse(BaseModel):
    id: int
    name: str
    lambda_val: float
    d_target: float

    class Config:
        orm_mode = True # This allows the model to be created from an ORM object

# --- FastAPI Application ---
app = FastAPI(
    title="Meta-Controller API",
    description="Manages policies for the Self-Cognitive Dissonance System.",
    version="0.2.0" # Version updated to reflect new functionality
)

@app.on_event("startup")
async def startup_event():
    print("Meta-Controller API starting up... Connecting to the database.")

@app.get("/")
def read_root():
    return {"message": "Welcome to the Meta-Controller API"}

@app.post("/policy", response_model=PolicyResponse)
def set_policy(policy_update: PolicyUpdate, db: Session = Depends(get_db)):
    """
    Set or update the dissonance policy in the database.
    """
    if policy_update.lambda_val < 0 or policy_update.d_target < 0:
        raise HTTPException(status_code=400, detail="Policy values must be non-negative.")

    # Get the existing policy or create a new one
    db_policy = db.query(models.Policy).filter(models.Policy.name == "current_policy").first()

    if db_policy:
        # Update existing policy
        db_policy.lambda_val = policy_update.lambda_val
        db_policy.d_target = policy_update.d_target
    else:
        # Create new policy
        db_policy = models.Policy(
            name="current_policy",
            lambda_val=policy_update.lambda_val,
            d_target=policy_update.d_target
        )
        db.add(db_policy)

    db.commit()
    db.refresh(db_policy)
    print(f"Policy in DB updated: lambda={db_policy.lambda_val}, D_target={db_policy.d_target}")
    return db_policy

@app.get("/policy", response_model=PolicyResponse)
def get_policy(db: Session = Depends(get_db)):
    """
    Retrieve the current dissonance policy from the database.
    If no policy exists, create a default one.
    """
    db_policy = db.query(models.Policy).filter(models.Policy.name == "current_policy").first()

    if db_policy is None:
        # If no policy is in the DB, create a default one and save it
        print("No policy found in the database, creating a default one.")
        default_policy = models.Policy(
            name="current_policy",
            lambda_val=0.1,
            d_target=0.05
        )
        db.add(default_policy)
        db.commit()
        db.refresh(default_policy)
        return default_policy

    return db_policy

@app.get("/metrics")
def get_metrics():
    """
    Placeholder for exposing Prometheus metrics.
    """
    return {
        "work_in_progress": "This endpoint will be integrated with Prometheus."
    }