"""National coordinator: match regional residuals (LLM), then route power
across the grid through neighbors (multi-hop BFS)."""

from collections import defaultdict
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langsmith import traceable

from src.routing import find_path


class RegionTransfer(BaseModel):
    src: str = Field(description="region sending power")
    dst: str = Field(description="region receiving power")
    amount: int = Field(description="megawatts to move")


class NationalPlan(BaseModel):
    transfers: list[RegionTransfer]


SYSTEM = """You balance power between REGIONS of the US grid. You get net SHORT
regions (need power) and net SURPLUS regions (spare power). Match surplus to
shortage -- distance does not matter, the grid will route the power.

PROCEDURE:
1. Sort short regions from biggest shortage to smallest.
2. Fully cover the biggest shortage first before moving to the next.
3. Never send more than a surplus region has. Do not split evenly.
4. Every transfer is between two different regions; amount > 0.
"""


def validate(transfers, short_names, surplus_names):
    clean = []
    for t in transfers:
        if t.src == t.dst or t.amount <= 0:
            continue
        if t.src not in surplus_names or t.dst not in short_names:
            continue
        clean.append((t.src, t.dst, t.amount))
    return clean


@traceable(name="route_matches")
def route_matches(matches: list[tuple]) -> list[tuple]:
    """Expand each region-to-region match into per-hop transfers via shortest path."""
    edges = defaultdict(int)
    for src, dst, amount in matches:
        path = find_path(src, dst)
        if not path or len(path) < 2:
            continue
        for a, b in zip(path, path[1:]):
            edges[(a, b)] += amount          # each hop carries the power
    return [(a, b, amt) for (a, b), amt in edges.items()]


@traceable(name="match_residuals")
def match_residuals(residuals: dict, planner=None) -> list[tuple]:
    """The LLM decision: match SURPLUS regions to SHORT regions.

    Returns region-to-region matches (pre-routing) as (src, dst, amount). This
    is the coordinator's actual judgment -- what the evals score. The routing
    below is deterministic plumbing, not a decision.
    """
    shorts = sorted([(r, v) for r, v in residuals.items() if v < 0], key=lambda x: x[1])
    surplus = sorted([(r, v) for r, v in residuals.items() if v > 0], key=lambda x: -x[1])

    if not shorts or not surplus:
        return []

    short_view = [{"region": r, "needs": -v} for r, v in shorts]
    surplus_view = [{"region": r, "has": v} for r, v in surplus]

    if planner is None:
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, max_tokens=1000)
        planner = llm.with_structured_output(NationalPlan)

    situation = f"SHORT regions: {short_view}\nSURPLUS regions: {surplus_view}"
    result = planner.invoke([("system", SYSTEM), ("human", situation)])

    return validate(result.transfers, {r for r, _ in shorts}, {r for r, _ in surplus})


@traceable(name="balance_national")
def balance_national(residuals: dict, planner=None) -> list[tuple]:
    """Full national step: match residuals (LLM), then route each match multi-hop."""
    matches = match_residuals(residuals, planner=planner)
    return route_matches(matches)            # expand matches into multi-hop routes