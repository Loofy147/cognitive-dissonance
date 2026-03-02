import gradio as gr
import requests
import os
import sys

# Add the project root to the Python path to access common config
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, project_root)

from services.common import config

EVALUATOR_URL = os.environ.get("EVALUATOR_URL", "http://evaluator:8000/run_once")

def run_evaluation(*args):
    features = {name: val for name, val in zip(config.FEATURE_NAMES, args)}
    try:
        response = requests.post(EVALUATOR_URL, json={"features": features})
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}

# Dynamically create inputs based on FEATURE_NAMES
inputs = []
for name in config.FEATURE_NAMES:
    if name == 'age':
        inputs.append(gr.Number(label="Age", value=40))
    elif name == 'gender':
        inputs.append(gr.Radio(choices=[("Male", 0), ("Female", 1)], label="Gender", value=0))
    else:
        # Most features in this dataset are binary (0/1)
        inputs.append(gr.Radio(choices=[("No", 0), ("Yes", 1)], label=name.replace("_", " ").title(), value=0))

iface = gr.Interface(
    fn=run_evaluation,
    inputs=inputs,
    outputs="json",
    title="Self-Cognitive-Dissonance System",
    description="Enter the clinical features to run the diabetes classification evaluation.",
)

if __name__ == "__main__":
    iface.launch(server_name="0.0.0.0", server_port=7860)
