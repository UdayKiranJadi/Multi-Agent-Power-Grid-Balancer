"""Fetch real EIA hourly data for ALL regions across a date range (ETL step).

Run once:  python fetch_data.py
Needs a free API key from https://www.eia.gov/opendata/ (put it in .env).
"""

import os
import requests
import pandas as pd
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.environ["EIA_API_KEY"]

URL = "https://api.eia.gov/v2/electricity/rto/region-data/data/"
PAGE = 5000   # EIA returns at most 5000 rows per request


def fetch_all(start: str, end: str) -> list[dict]:
    """Pull Demand (D) and Net generation (NG) for EVERY region, with paging."""
    rows = []
    offset = 0
    while True:
        params = {
            "api_key": API_KEY,
            "frequency": "hourly",
            "data[0]": "value",
            "facets[type][]": ["D", "NG"],   # no respondent filter = ALL regions
            "start": start,
            "end": end,
            "offset": offset,
            "length": PAGE,
        }
        batch = requests.get(URL, params=params).json()["response"]["data"]
        if not batch:                # empty page = we've got everything
            break
        rows.extend(batch)
        offset += PAGE
        print(f"  fetched {len(rows)} rows so far...")
    return rows


def build_csv(start: str, end: str, out: str = "data/grid.csv") -> None:
    records = fetch_all(start, end)

    # Skip rows where the value is missing (real data has gaps)
    clean = [r for r in records if r.get("value") is not None]
    print(f"  kept {len(clean)} of {len(records)} rows after dropping empty values")

    long_df = pd.DataFrame([{
        "timestamp": r["period"],
        "region": r["respondent"],        # the balancing-authority code (CISO, PJM, ...)
        "type": r["type"],
        "value": float(r["value"]),
    } for r in clean])

    wide = long_df.pivot_table(
        index=["timestamp", "region"],
        columns="type",
        values="value",
    ).reset_index()

    wide = wide.rename(columns={"D": "demand", "NG": "generation"})
    wide = wide.dropna(subset=["demand", "generation"])   # drop incomplete pairs
    wide.to_csv(out, index=False)
    print(f"wrote {len(wide)} rows across {wide['region'].nunique()} regions to {out}")


if __name__ == "__main__":
    # one month of data, ALL regions
    build_csv(start="2024-01-01T00", end="2024-02-01T00")