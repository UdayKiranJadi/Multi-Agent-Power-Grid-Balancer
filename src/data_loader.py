"""Loads real EIA hourly demand data and hands one hour to the agents."""

import pandas as pd


def load_grid_data(csv_path: str) -> pd.DataFrame:
    """Read the whole CSV once into a table."""
    return pd.read_csv(csv_path, parse_dates=["timestamp"])


def get_hour(df: pd.DataFrame, timestamp: str) -> dict[str, dict]:
    """Return raw supply & demand for every region at one hour.

    Example return:
        {
            "A": {"demand": 1000, "supply": 1000},
            "B": {"demand": 1200, "supply": 1000},
            "C": {"demand":  800, "supply": 1100},
        }
    """
    rows = df[df["timestamp"] == timestamp]
    data = {}
    for _, row in rows.iterrows():
        data[row["region"]] = {
            "demand": int(row["demand"]),
            "supply": int(row["generation"]),
        }
    return data