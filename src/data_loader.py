"""Loads real EIA hourly demand data and hands one hour to the agents."""

import pandas as pd

# EIA reports BOTH individual operators AND aggregate regions in the same feed.
# These codes are aggregates (whole regions / the whole country) -- excluding
# them avoids double-counting a region against the operators inside it.
AGGREGATES = {
    "US48",                                    # entire lower 48
    "CAL", "CAR", "CENT", "FLA", "MIDA",       # the 13 EIA region aggregates
    "MIDW", "NE", "NW", "NY", "SE",
    "SW", "TEN", "TEX",
}


def load_grid_data(csv_path: str) -> pd.DataFrame:
    """Read the whole CSV once into a table."""
    return pd.read_csv(csv_path, parse_dates=["timestamp"])


def get_hour(df: pd.DataFrame, timestamp: str) -> dict[str, dict]:
    """Return raw supply & demand for every INDIVIDUAL operator at one hour."""
    rows = df[df["timestamp"] == timestamp]
    data = {}
    for _, row in rows.iterrows():
        region = row["region"]
        if region in AGGREGATES:          # skip aggregates -- keep real operators only
            continue
        data[region] = {
            "demand": int(row["demand"]),
            "supply": int(row["generation"]),
        }
    return data