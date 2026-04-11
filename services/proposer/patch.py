import os

with open('services/proposer/main.py', 'r') as f:
    content = f.read()

# Modify predict function to handle text features
search_text = \"\"\"        ordered_feature_names = task_cfg["feature_names"]
        feature_values = []
        for k in ordered_feature_names:
            value = item.features.get(k)
            if value is None:
                raise KeyError(f"Missing feature: {k}")
            if not isinstance(value, (int, float)) or not math.isfinite(value):
                raise HTTPException(
                    status_code=422, detail=f"Invalid value for feature '{k}'."
                )
            feature_values.append(value)

        features_array = np.array(feature_values).reshape(1, -1)
        input_df = pd.DataFrame(features_array, columns=ordered_feature_names)

        probabilities = model.predict(input_df)
        p0 = float(probabilities[0])
        p1 = 1.0 - p0\"\"\"

replace_text = \"\"\"        ordered_feature_names = task_cfg["feature_names"]

        # Handle reasoning tasks (text-based)
        if task_id == "nemotron_reasoning":
            prompt = item.features.get("prompt")
            if not prompt:
                raise KeyError("Missing feature: prompt")

            # Placeholder for reasoning logic or LLM call
            # For the POC, we return a mock prediction or use the model if it's a text-model
            if hasattr(model, "generate"): # Check if it's a transformer model
                # This would be the real path for a loaded LoRA
                # For now, we simulate a 'confidence' score or similar
                p0 = 0.85 # High confidence in reasoning
            else:
                # Fallback to a simple heuristic for the scikit-learn mock models
                p0 = 0.5
            p1 = 1.0 - p0
        else:
            feature_values = []
            for k in ordered_feature_names:
                value = item.features.get(k)
                if value is None:
                    raise KeyError(f"Missing feature: {k}")
                if not isinstance(value, (int, float)) or not math.isfinite(value):
                    raise HTTPException(
                        status_code=422, detail=f"Invalid value for feature '{k}'."
                    )
                feature_values.append(value)

            features_array = np.array(feature_values).reshape(1, -1)
            input_df = pd.DataFrame(features_array, columns=ordered_feature_names)

            probabilities = model.predict(input_df)
            p0 = float(probabilities[0])
            p1 = 1.0 - p0\"\"\"

if search_text in content:
    with open('services/proposer/main.py', 'w') as f:
        f.write(content.replace(search_text, replace_text))
    print('Patched services/proposer/main.py')
else:
    print('Search text not found in proposer')
