"""The shared clipboard every node reads and writes."""

import operator
from typing import Annotated, TypedDict


class RegionReport(TypedDict):
    region: str      # which region, e.g. "A"
    gap: int         # negative = short, positive = surplus (in MW)
    status: str      # "short", "ok", or "surplus"


class GridState(TypedDict):
    # INPUT: this hour's raw numbers, seeded when we start the graph.
    # Shape: {"A": {"demand": 1000, "supply": 1000}, ...}
    hour: dict[str, dict]

    # Every region agent appends its report here (parallel-safe via operator.add).
    reports: Annotated[list[RegionReport], operator.add]

    # The coordinator writes its final decision here.
    plan: list[tuple]