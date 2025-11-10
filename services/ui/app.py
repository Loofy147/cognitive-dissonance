import gradio as gr
import requests
import os

EVALUATOR_URL = os.environ.get("EVALUATOR_URL", "http://localhost:8003/run_once")

def run_evaluation(f1, f2):
    features = {"f1": f1, "f2": f2}
    try:
        response = requests.post(EVALUATOR_URL, json={"features": features})
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}

iface = gr.Interface(
    fn=run_evaluation,
    inputs=[
        gr.Number(label="Feature 1"),
        gr.Number(label="Feature 2"),
    ],
    outputs="json",
    title="Self-Cognitive-Dissonance System",
    description="Enter two features to run the evaluation.",
)

if __name__ == "__main__":
    iface.launch()
