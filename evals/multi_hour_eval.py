"""Batch eval: score the agent's residuals against real interchange, over MANY hours.

Residuals come from local balancing (plain code), so this runs over the whole
month with NO LLM calls -- fast and free.

Metrics:
  - direction accuracy (importer vs exporter) -- aggregates cleanly across regions
  - PER-REGION magnitude correlation -- correlate within each region, then average
    (pooling different-sized regions into one correlation is meaningless)
"""

import pandas as pd
from collections import defaultdict

from src.data_loader import get_hour
from src.hierarchy import compute_residuals


def run(max_hours: int | None = None) -> None:
    grid = pd.read_csv("data/grid.csv")
    inter = pd.read_csv("data/interchange.csv")

    timestamps = sorted(set(grid["timestamp"].unique()) & set(inter["timestamp"].unique()))
    if max_hours:
        timestamps = timestamps[:max_hours]

    actual = {(r["timestamp"], r["region"]): r["interchange"] for _, r in inter.iterrows()}

    correct = 0
    total = 0
    per_region = defaultdict(lambda: {"correct": 0, "total": 0, "preds": [], "reals": []})

    for ts in timestamps:
        hour = get_hour(grid, ts)
        _, residuals = compute_residuals(hour)
        for region, pred in residuals.items():
            key = (ts, region)
            if key not in actual:
                continue
            real = actual[key]
            same = (pred >= 0) == (real >= 0)
            correct += same
            total += 1
            pr = per_region[region]
            pr["correct"] += same
            pr["total"] += 1
            pr["preds"].append(pred)
            pr["reals"].append(real)

    print(f"Evaluated {len(timestamps)} hours, {total} region-hours\n")
    print(f"Overall direction accuracy: {correct}/{total} = {correct/total:.1%}\n")

    print(f"{'Region':6} {'Direction':>10} {'Correlation':>12} {'Hours':>7}")
    print("-" * 40)
    corrs = []
    rows = []
    for region, d in per_region.items():
        acc = d["correct"] / d["total"]
        corr = pd.Series(d["preds"]).corr(pd.Series(d["reals"]))
        corrs.append(corr)
        rows.append((region, acc, corr, d["total"]))

    for region, acc, corr, n in sorted(rows, key=lambda x: x[1]):
        print(f"{region:6} {acc:>9.1%} {corr:>12.2f} {n:>7}")

    print("-" * 40)
    mean_corr = sum(corrs) / len(corrs)
    print(f"Mean per-region correlation: {mean_corr:.2f}")


if __name__ == "__main__":
    run()