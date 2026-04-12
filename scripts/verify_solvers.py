import os
import sys

import pandas as pd

sys.path.insert(0, os.getcwd())
from services.common.solvers import wonderland_solver  # noqa: E402


def verify():
    df = pd.read_csv("data/nemotron/train.csv")
    correct = 0
    total = 0

    # Check 1000 samples
    samples = df.head(2000)
    for idx, row in samples.iterrows():
        ans = wonderland_solver(row["prompt"])
        total += 1
        if not ans:
            continue

        # Competition metric: matches ground truth exactly as string or relative numerical tolerance
        try:
            exp_f = float(row["answer"])
            act_f = float(ans)
            if abs(act_f - exp_f) < 0.1:
                correct += 1
                continue
        except Exception:
            pass

        if str(ans).strip() == str(row["answer"]).strip():
            correct += 1

    print(f"Verified {total} samples.")
    print(f"Correct: {correct}")
    if total > 0:
        print(f"Total System Accuracy: {correct/total:.2%}")


if __name__ == "__main__":
    verify()
