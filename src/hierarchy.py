"""Orchestrator: run the full hierarchy -- local balancing, then national."""

from collections import defaultdict

from src.region_agent import make_region_agent
from src.regions import region_of
from src.local_coordinator import balance_region
from src.national_coordinator import balance_national


def compute_residuals(hour: dict) -> tuple[list, dict]:
    """Steps 1-3: reports -> group by region -> local balancing.
    Returns (local_transfers, residuals). No LLM -- pure code, fast and free.
    """
    reports = []
    for operator in hour:
        reports += make_region_agent(operator)({"hour": hour})["reports"]

    groups = defaultdict(list)
    for r in reports:
        region = region_of(r["region"])
        if region is None:
            continue
        groups[region].append(r)

    local_transfers = []
    residuals = {}
    for region, region_reports in groups.items():
        transfers, residual = balance_region(region_reports)
        local_transfers += transfers
        residuals[region] = residual
    return local_transfers, residuals


def run_hierarchy(hour: dict, planner=None) -> dict:
    """Full run: local balancing + the national LLM match."""
    local_transfers, residuals = compute_residuals(hour)
    national_transfers = balance_national(residuals, planner=planner)
    return {
        "local_transfers": local_transfers,
        "national_transfers": national_transfers,
        "residuals": residuals,
    }