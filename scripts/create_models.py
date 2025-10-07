import pickle
import numpy as np
from sklearn.neural_network import MLPClassifier
from sklearn.datasets import make_moons
import os

def create_and_save_model(model_path, hidden_layer_sizes, activation, solver, alpha):
    """Trains a Multi-layer Perceptron model and saves it."""
    # Create a non-linear dataset
    X, y = make_moons(n_samples=200, noise=0.2, random_state=42)

    # Train model
    model = MLPClassifier(
        hidden_layer_sizes=hidden_layer_sizes,
        activation=activation,
        solver=solver,
        alpha=alpha,
        random_state=1,
        max_iter=1000,
    )
    model.fit(X, y)

    # Ensure the directory exists
    os.makedirs(os.path.dirname(model_path), exist_ok=True)

    # Save model
    with open(model_path, 'wb') as f:
        pickle.dump(model, f)
    print(f"Model with architecture {hidden_layer_sizes} saved to {model_path}")

if __name__ == "__main__":
    print("Generating new MLP models based on a non-linear dataset...")

    # Create proposer model (a standard MLP)
    create_and_save_model(
        "services/models/proposer.pkl",
        hidden_layer_sizes=(10, 5),
        activation='relu',
        solver='adam',
        alpha=1e-5
    )

    # Create critic model (a different MLP architecture to create dissonance)
    create_and_save_model(
        "services/models/critic.pkl",
        hidden_layer_sizes=(5, 10, 5), # Deeper but maybe less efficient
        activation='tanh',
        solver='adam',
        alpha=1e-4 # More regularization
    )
    print("\nBoth MLP models created successfully.")