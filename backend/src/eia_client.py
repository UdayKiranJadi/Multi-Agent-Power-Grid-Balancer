"""Live EIA fetch: pull ONE hour of real grid data on demand.

The static CSV (fetch_data.py) is great for evals and offline demos, but it
freezes the dashboard on one month. This module hits the EIA API per requested
timestamp so the user can scrub to ANY hour -- or jump to the latest published
hour ("live"). Same output shape as data_loader.get_hour, so the hierarchy
doesn't know or care where the numbers came from.

EIA hourly data publishes with a lag, so "latest" means the most recent
*complete* hour EIA has posted -- typically a few hours behind wall-clock.
"""

import os
import requests

from src.data_loader import AGGREGATES

EIA_URL = "https://api.eia.gov/v2/electricity/rto/region-data/data/"
TIMEOUT = 30


def _api_key() -> str | None:
    return os.getenv("EIA_API_KEY")


def available() -> bool:
    """True if we can serve live data (an API key is configured)."""
    return bool(_api_key())


def fetch_hour(timestamp: str) -> dict[str, dict]:
    """Real demand + generation for every INDIVIDUAL operator at one hour.

    Returns {region: {"demand": int, "supply": int}} -- exactly what
    data_loader.get_hour produces, but live from the API. Empty dict if EIA has
    no data for that hour yet.
    """
    if not _api_key():
        raise RuntimeError("EIA_API_KEY not set -- cannot fetch live data")

    params = {
        "api_key": _api_key(),
        "frequency": "hourly",
        "data[0]": "value",
        "facets[type][]": ["D", "NG"],      # Demand + Net generation, all regions
        "start": timestamp,                  # EIA period filters are inclusive
        "end": timestamp,
        "length": 5000,
    }
    resp = requests.get(EIA_URL, params=params, timeout=TIMEOUT)
    resp.raise_for_status()
    data = resp.json()["response"]["data"]

    by_region: dict[str, dict] = {}
    for r in data:
        if r.get("value") is None:
            continue
        if r["period"] != timestamp:         # guard against range creep
            continue
        region = r["respondent"]
        if region in AGGREGATES:             # skip region/national aggregates
            continue
        slot = by_region.setdefault(region, {})
        if r["type"] == "D":
            slot["demand"] = int(float(r["value"]))
        elif r["type"] == "NG":
            slot["supply"] = int(float(r["value"]))

    # keep only operators that reported BOTH numbers this hour
    return {reg: v for reg, v in by_region.items()
            if "demand" in v and "supply" in v}


def latest_timestamp() -> str | None:
    """The most recent hour EIA has published (one row, newest first)."""
    if not _api_key():
        return None

    params = {
        "api_key": _api_key(),
        "frequency": "hourly",
        "data[0]": "value",
        "facets[type][]": "D",
        "sort[0][column]": "period",
        "sort[0][direction]": "desc",
        "length": 1,
    }
    resp = requests.get(EIA_URL, params=params, timeout=TIMEOUT)
    resp.raise_for_status()
    data = resp.json()["response"]["data"]
    return data[0]["period"] if data else None
