import os
import sys

import gradio as gr
import requests

# Add the project root to the Python path to access common config
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, project_root)

from services.common import config  # noqa: E402  # noqa: E402

EVALUATOR_URL = os.environ.get("EVALUATOR_URL", "http://evaluator:8000/run_once")


def create_ui():
    with gr.Blocks(title="Self-Cognitive-Dissonance System") as demo:
        gr.Markdown("# Private Model Improvement System")
        gr.Markdown(
            "Select a dataset (task) to run through the private cognitive dissonance loop."
        )

        task_id_dropdown = gr.Dropdown(
            choices=list(config.TASKS.keys()),
            value=config.DEFAULT_TASK,
            label="Kaggle Dataset (Task ID)",
        )

        @gr.render(inputs=[task_id_dropdown])
        def render_inputs(task_id):
            task_cfg = config.get_task_config(task_id)
            input_fields = []
            with gr.Column():
                for name in task_cfg["feature_names"]:
                    if name.lower() == "age":
                        input_fields.append(gr.Number(label="Age", value=40))
                    elif name.lower() == "gender" or name.lower() == "sex":
                        input_fields.append(
                            gr.Radio(
                                choices=[("Male", 0), ("Female", 1)],
                                label=name,
                                value=0,
                            )
                        )
                    else:
                        input_fields.append(
                            gr.Number(label=name.replace("_", " ").title(), value=0)
                        )

                submit_btn = gr.Button("Run Private Dissonance Loop")
                output = gr.JSON(label="Result")

                def run_loop(task, *args):
                    # args will contain values from input_fields
                    features = {
                        name: val for name, val in zip(task_cfg["feature_names"], args)
                    }
                    try:
                        response = requests.post(
                            EVALUATOR_URL, json={"features": features, "task_id": task}
                        )
                        response.raise_for_status()
                        return response.json()
                    except requests.exceptions.RequestException as e:
                        return {"error": str(e)}

                submit_btn.click(
                    fn=run_loop,
                    inputs=[task_id_dropdown] + input_fields,
                    outputs=output,
                )

    return demo


if __name__ == "__main__":
    demo = create_ui()
    demo.launch(server_name="0.0.0.0", server_port=7860)
