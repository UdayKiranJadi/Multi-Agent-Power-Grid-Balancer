"""The coordinator: collect reports -> match need with surplus -> decide transfers."""

from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from src.state import GridState

TOP_N = 10   # only reason about the N most significant regions on each side


class Transfer(BaseModel):
    src: str = Field(description="region sending power")
    dst: str = Field(description="region receiving power")
    amount: int = Field(description="megawatts to move")


class Plan(BaseModel):
    transfers: list[Transfer]


SYSTEM = """You balance a power grid. You get SHORT regions (need power) and
SURPLUS regions (spare power). Decide power transfers to cover shortages.

FOLLOW THIS EXACT PROCEDURE:
1. Sort the short regions from BIGGEST shortage to smallest.
2. Take the biggest shortage first. FULLY cover it using available surplus
   before you give ANY power to the next region.
3. Only after it is fully covered (or surplus runs out) move to the next
   biggest shortage with whatever surplus is left.
4. Never send more than a surplus region actually has.
5. Do NOT split surplus evenly. Priority is strict: biggest shortage first.
6. Keep the plan SHORT: at most one or two transfers per short region.
   Do not create many tiny transfers. Stop once surplus runs out.
7. A transfer must be between TWO DIFFERENT regions (never region to itself),
   and the amount must be greater than zero.

WORKED EXAMPLE:
SHORT: A needs 200, B needs 300.  SURPLUS: C has 400.
Correct: C -> B 300, then C -> A 100.
WRONG: C -> A 200, C -> B 200 (even-splitting -- never do this).
"""


def validate(transfers, shorts, surplus):
    """Plain-code safety net: drop transfers the LLM shouldn't have made."""
    short_names = {r["region"] for r in shorts}
    surplus_names = {r["region"] for r in surplus}

    clean = []
    for t in transfers:
        if t.src == t.dst:                      # no self-transfers
            continue
        if t.amount <= 0:                       # no zero/negative moves
            continue
        if t.src not in surplus_names:          # source must actually have surplus
            continue
        if t.dst not in short_names:            # destination must actually be short
            continue
        clean.append((t.src, t.dst, t.amount))
    return clean


def coordinator(state: GridState) -> dict:
    reports = state["reports"]

    shorts = sorted((r for r in reports if r["status"] == "short"),
                    key=lambda r: r["gap"])
    surplus = sorted((r for r in reports if r["status"] == "surplus"),
                     key=lambda r: -r["gap"])

    if not shorts or not surplus:
        return {"plan": []}

    shorts = shorts[:TOP_N]
    surplus = surplus[:TOP_N]

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, max_tokens=1000)
    planner = llm.with_structured_output(Plan)

    short_view = [{"region": r["region"], "needs": -r["gap"]} for r in shorts]
    surplus_view = [{"region": r["region"], "has": r["gap"]} for r in surplus]

    situation = f"SHORT regions: {short_view}\nSURPLUS regions: {surplus_view}"
    result = planner.invoke([("system", SYSTEM), ("human", situation)])

    # plain-code validation layer -- the LLM reasons, code checks
    plan = validate(result.transfers, shorts, surplus)
    return {"plan": plan}