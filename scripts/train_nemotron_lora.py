import json
import os

import pandas as pd
from peft import LoraConfig, TaskType


def train():
    print("Starting LoRA fine-tuning for Nemotron-3-Nano (Simulated)...")

    # Load dataset
    df = pd.read_csv("data/nemotron/train.csv")
    print(f"Loaded {len(df)} training samples.")

    # Configure LoRA
    lora_config = LoraConfig(
        r=32,
        lora_alpha=64,
        target_modules=["q_proj", "v_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type=TaskType.CAUSAL_LM,
    )

    print(f"LoRA configuration created with rank {lora_config.r}.")

    # Logic to create submission.zip
    os.makedirs("submission", exist_ok=True)
    # Mocking the adapter_config.json
    adapter_config = {
        "base_model_name_or_path": "nvidia/nemotron-3-nano-30b",
        "peft_type": "LORA",
        "r": 32,
        "lora_alpha": 64,
        "target_modules": ["q_proj", "v_proj"],
    }
    with open("submission/adapter_config.json", "w") as f:
        json.dump(adapter_config, f)

    print("adapter_config.json created in submission/ directory.")

    print("LoRA training script (skeleton) completed.")


if __name__ == "__main__":
    train()
