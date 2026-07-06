"""National coordinator: balance the regional residuals with the LLM."""

from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI


class RegionTransfer(BaseModel):
    src: str = Field(description="region sending power")
    dst: str = Field(description="region receiving power")
    amount: int = Field(description="megawatts to move")


class NationalPlan(BaseModel):
    transfers: list[RegionTransfer]


SYSTEM = """You balance power between REGIONS of the US grid. You get regions
that are net SHORT (need power) and net SURPLUS (spare power).

FOLLOW THIS EXACT PROCEDURE:
1. Sort short regions from BIGGEST shortage to smallest.
2. Fully cover the biggest shortage first before giving power to the next.
3. Never send more than a surplus region actually has.
4. Do NOT split surplus evenly. Priority is strict: biggest shortage first.
5. Every transfer is between two DIFFERENT regions, amount greater than zero.
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


def balance_national(residuals: dict, planner=None) -> list[tuple]:
    """residuals: {region: net_MW}. Returns inter-region transfers."""
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

    return validate(result.transfers,
                    {r for r, _ in shorts},
                    {r for r, _ in surplus})