"""Production API: expose the power grid balancer as a web service."""

import os

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from src.data_loader import load_grid_data, get_hour
from src.hierarchy import run_hierarchy
from src import eia_client

app = FastAPI(title="Power Grid Balancer")

# Which browser origins may call this API. Config, not code: set
# ALLOWED_ORIGINS in the environment (comma-separated) to lock prod down to
# your real frontend URL. Defaults to "*" so local dev / the demo keep working.
_origins = os.getenv("ALLOWED_ORIGINS", "*")
allow_origins = ["*"] if _origins == "*" else [o.strip() for o in _origins.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Optional static fallback: the checked-out month of data, if present. Live EIA
# is the primary source; this just keeps the demo working offline / without a key.
try:
    GRID = load_grid_data("data/grid.csv")
except FileNotFoundError:
    GRID = None

# simple in-memory cache: timestamp -> computed result
CACHE = {}


def resolve_hour(timestamp: str) -> dict:
    """Get one hour of grid data: live from EIA first, static CSV as a fallback.

    Live means the user can scrub to ANY hour; the CSV only covers one month.
    """
    if eia_client.available():
        try:
            hour = eia_client.fetch_hour(timestamp)
            if hour:
                return hour
        except Exception:
            pass                       # EIA hiccup -> fall through to the CSV
    if GRID is not None:
        return get_hour(GRID, timestamp)
    return {}


@app.get("/health")
def health():
    return {"status": "ok", "live": eia_client.available(), "has_static": GRID is not None}


@app.get("/latest")
def latest():
    """The most recent hour we can serve -- live EIA's newest, else the CSV's max."""
    ts = eia_client.latest_timestamp()
    if ts is None and GRID is not None:
        ts = str(GRID["timestamp"].max())[:13]     # "YYYY-MM-DDTHH"
    if ts is None:
        raise HTTPException(status_code=503, detail="No data source available")
    return {"timestamp": ts, "live": eia_client.available()}


@app.get("/balance/{timestamp}")
def balance(timestamp: str):
    if timestamp in CACHE:
        return {"cached": True, **CACHE[timestamp]}

    hour = resolve_hour(timestamp)
    if not hour:
        raise HTTPException(status_code=404, detail=f"No data for {timestamp}")

    result = run_hierarchy(hour)
    response = {
        "timestamp": timestamp,
        "residuals": result["residuals"],
        "local_transfers": result["local_transfers"],
        "national_transfers": result["national_transfers"],
    }
    CACHE[timestamp] = response
    return {"cached": False, **response}