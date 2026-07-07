"""Production API: expose the power grid balancer as a web service."""

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException

from src.data_loader import load_grid_data, get_hour
from src.hierarchy import run_hierarchy

app = FastAPI(title="Power Grid Balancer")

# load the data ONCE at startup, not on every request
GRID = load_grid_data("data/grid.csv")

# simple in-memory cache: timestamp -> computed result
CACHE = {}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/balance/{timestamp}")
def balance(timestamp: str):
    # 1. cache hit? return instantly, no LLM call
    if timestamp in CACHE:
        return {"cached": True, **CACHE[timestamp]}

    # 2. cache miss: compute it
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

    # 3. store for next time
    CACHE[timestamp] = response
    return {"cached": False, **response}