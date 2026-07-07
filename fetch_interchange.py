"""Fetch real hourly INTERCHANGE for each EIA region -- our ground truth.

Total Interchange (TI) = the actual net power a region exchanged with the rest
of the grid that hour. This is what really happened -- we score our agent
against it.

Run once:  python fetch_interchange.py
"""

import os
import requests
import pandas as pd
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.environ["EIA_API_KEY"]

URL = "https://api.eia.gov/v2/electricity/rto/region-data/data/"
PAGE = 5000

# the 13 EIA region aggregates -- we want each region's real net flow
REGIONS = ["CAL", "CAR", "CENT", "FLA", "MIDA", "MIDW",
           "NE", "NW", "NY", "SE", "SW", "TEN", "TEX"]


def fetch_interchange(start: str, end: str) -> list[dict]:
    """Pull Total Interchange (TI) for every region, with paging."""
    rows = []
    offset = 0
    while True:
        params = {
            "api_key": API_KEY,
            "frequency": "hourly",
            "data[0]": "value",
            "facets[respondent][]": REGIONS,   # the 13 regions
            "facets[type][]": "TI",            # TI = total interchange (real net flow)
            "start": start,
            "end": end,
            "offset": offset,
            "length": PAGE,
        }
        batch = requests.get(URL, params=params).json()["response"]["data"]
        if not batch:
            break
        rows.extend(batch)
        offset += PAGE
        print(f"  fetched {len(rows)} rows so far...")
    return rows


def build_csv(start: str, end: str, out: str = "data/interchange.csv") -> None:
    records = fetch_interchange(start, end)
    clean = [r for r in records if r.get("value") is not None]

    df = pd.DataFrame([{
        "timestamp": r["period"],
        "region": r["respondent"],
        "interchange": float(r["value"]),   # real net flow (MW)
    } for r in clean])

    df.to_csv(out, index=False)
    print(f"wrote {len(df)} rows across {df['region'].nunique()} regions to {out}")


if __name__ == "__main__":
    # same month as your grid data
    build_csv(start="2024-01-01T00", end="2024-02-01T00")