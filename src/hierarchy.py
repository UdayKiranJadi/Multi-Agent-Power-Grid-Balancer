"""Orchestrator: run the full hierarchy -- local balancing, then national."""

from collections import defaultdict

from src.region_agent import make_region_agent
from src.regions import region_of
from src.local_coordinator import balance_region
from src.national_coordinator import balance_national


def run_hierarchy(hour: dict, planner=None) -> dict:
    # 1. build operator reports (reuse the region agents)
    reports = []
    for operator in hour:
        reports += make_region_agent(operator)({"hour": hour})["reports"]

    # 2. group operators by their region
    groups = defaultdict(list)
    for r in reports:
        region = region_of(r["region"])
        if region is None:
            continue
        groups[region].append(r)

    # 3. local balancing per region -> local transfers + residual
    local_transfers = []
    residuals = {}
    for region, region_reports in groups.items():
        transfers, residual = balance_region(region_reports)
        local_transfers += transfers
        residuals[region] = residual

    # 4. national coordinator matches the residuals (the one LLM call)
    national_transfers = balance_national(residuals, planner=planner)

    # 5. combine
    return {
        "local_transfers": local_transfers,
        "national_transfers": national_transfers,
        "residuals": residuals,
    }