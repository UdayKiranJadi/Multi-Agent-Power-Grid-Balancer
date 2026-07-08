"""Production API: expose the power grid balancer as a web service."""

import os

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from src.data_loader import load_grid_data, get_hour
from src.hierarchy import run_hierarchy

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

# load the data ONCE at startup, not on every request
GRID = load_grid_data("data/grid.csv")

# simple in-memory cache: timestamp -> computed result
CACHE = {}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/balance/{timestamp}")
def balance(timestamp: str):
    if timestamp in CACHE:
        return {"cached": True, **CACHE[timestamp]}

    hour = get_hour(GRID, timestamp)
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