"""Fix region bias (e.g. NW hydro) with a GUARDED offset correction.

Learn each region's bias offset on training hours, but only KEEP the offset if it
improves that region's direction accuracy on the training set. Regions that are
already accurate (or would be hurt) get no correction. Proven on a held-out test set.
"""

import pandas as pd
from collections import defaultdict

from src.data_loader import get_hour
from src.hierarchy import compute_residuals


def run(train_frac: float = 0.7) -> None:
    grid = pd.read_csv("data/grid.csv")
    inter = pd.read_csv("data/interchange.csv")
    timestamps = sorted(set(grid["timestamp"].unique()) & set(inter["timestamp"].unique()))
    actual = {(r["timestamp"], r["region"]): r["interchange"] for _, r in inter.iterrows()}

    split = int(len(timestamps) * train_frac)
    train_ts, test_ts = timestamps[:split], timestamps[split:]

    def residuals_for(ts_list):
        return {ts: compute_residuals(get_hour(grid, ts))[1] for ts in ts_list}

    train_res = residuals_for(train_ts)
    test_res = residuals_for(test_ts)

    # 1. LEARN raw offset per region on TRAIN
    diffs = defaultdict(list)
    for ts in train_ts:
        for region, pred in train_res[ts].items():
            if (ts, region) in actual:
                diffs[region].append(actual[(ts, region)] - pred)
    raw_offset = {r: sum(v) / len(v) for r, v in diffs.items()}

    # helper: a region's direction accuracy on a given set of hours
    def acc(region, res_by_ts, ts_list, off):
        c = t = 0
        for ts in ts_list:
            pred = res_by_ts[ts].get(region)
            if pred is None or (ts, region) not in actual:
                continue
            real = actual[(ts, region)]
            c += ((pred + off) >= 0) == (real >= 0)
            t += 1
        return c / t if t else 0

    # 2. GUARD: keep the offset only if it helps on TRAIN
    offset = {}
    for region, off in raw_offset.items():
        base = acc(region, train_res, train_ts, 0)
        corrected = acc(region, train_res, train_ts, off)
        offset[region] = off if corrected > base else 0.0

    # 3. EVALUATE on held-out TEST, before vs after guarded correction
    print(f"Train hours: {len(train_ts)} | Test hours: {len(test_ts)}\n")
    print("Held-out test-set direction accuracy (guarded):")
    print(f"{'Region':6} {'Before':>8} {'After':>8} {'Offset(MW)':>12}")
    print("-" * 38)
    nb = tb = ta = 0
    rows = []
    for region in offset:
        b = acc(region, test_res, test_ts, 0)
        a = acc(region, test_res, test_ts, offset[region])
        n = sum(1 for ts in test_ts if region in test_res[ts] and (ts, region) in actual)
        rows.append((region, b, a, offset[region]))
        nb += n; tb += b * n; ta += a * n

    for region, b, a, off in sorted(rows, key=lambda x: x[1]):
        print(f"{region:6} {b:>7.1%} {a:>8.1%} {off:>12.0f}")

    print("-" * 38)
    print(f"Overall: {tb/nb:.1%}  ->  {ta/nb:.1%}")


if __name__ == "__main__":
    run()