import pickle
import numpy as np
from sklearn.linear_model import LogisticRegression
import os

def create_and_save_model(model_path, C, class_weight):
    """Trains a simple logistic regression model and saves it."""
    # Create dummy data
    X = np.random.rand(100, 2)
    y = (X[:, 0] + X[:, 1] > 1).astype(int)

    # Train model
    model = LogisticRegression(C=C, class_weight=class_weight)
    model.fit(X, y)

    # Ensure the directory exists
    os.makedirs(os.path.dirname(model_path), exist_ok=True)

    # Save model
    with open(model_path, 'wb') as f:
        pickle.dump(model, f)
    print(f"Model saved to {model_path}")

if __name__ == "__main__":
    # Create proposer model (a standard classifier)
    create_and_save_model(
        "services/models/proposer.pkl",
        C=1.0,
        class_weight=None
    )

    # Create critic model (a slightly different classifier to create dissonance)
    create_and_save_model(
        "services/models/critic.pkl",
        C=0.2, # Different regularization
        class_weight={0: 0.6, 1: 0.4} # Skewed weights
    )
    print("Both models created successfully.")