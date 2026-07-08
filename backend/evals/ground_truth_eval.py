"""Score the agent's residuals against REAL grid interchange (ground truth).

Two honest metrics:
  1. Direction accuracy -- does the agent get importer vs exporter right?
  2. Magnitude correlation -- do the agent's residuals track the real flows?
"""

from dotenv import load_dotenv
load_dotenv()

import pandas as pd

from src.data_loader import load_grid_data, get_hour
from src.hierarchy import run_hierarchy


def load_real_interchange(path: str, timestamp: str) -> dict:
    """Real net flow per region for one hour. {region: interchange_MW}."""
    df = pd.read_csv(path)
    rows = df[df["timestamp"] == timestamp]
    return {r["region"]: r["interchange"] for _, r in rows.iterrows()}


def evaluate(timestamp: str, planner=None) -> None:
    # 1. what the AGENT thinks each region's net position is (residuals)
    grid = load_grid_data("data/grid.csv")
    hour = get_hour(grid, timestamp)
    result = run_hierarchy(hour, planner=planner)
    predicted = result["residuals"]                       # {region: residual_MW}

    # 2. what the grid ACTUALLY did
    actual = load_real_interchange("data/interchange.csv", timestamp)

    # 3. compare region by region
    print(f"{'Region':6} {'Predicted':>10} {'Actual':>10} {'Dir':>5}")
    print("-" * 36)
    correct_dir = 0
    total = 0
    preds, reals = [], []
    for region in sorted(predicted):
        if region not in actual:
            continue
        p = predicted[region]
        a = actual[region]
        # same sign = agent got the direction (importer/exporter) right
        same = (p >= 0) == (a >= 0)
        correct_dir += same
        total += 1
        preds.append(p)
        reals.append(a)
        print(f"{region:6} {p:>10.0f} {a:>10.0f} {'OK' if same else 'X':>5}")

    # 4. metrics
    print("-" * 36)
    print(f"Direction accuracy: {correct_dir}/{total} = {correct_dir/total:.0%}")

    # magnitude correlation (how well residuals track real flows)
    s = pd.Series(preds).corr(pd.Series(reals))
    print(f"Magnitude correlation: {s:.2f}  (1.0 = perfect, 0 = none)")


if __name__ == "__main__":
    evaluate("2024-01-01T00")