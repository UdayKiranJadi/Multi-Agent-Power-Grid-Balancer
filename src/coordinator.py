"""The coordinator: collect reports -> match need with surplus -> decide transfers."""

from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from src.state import GridState


class Transfer(BaseModel):
    src: str = Field(description="region sending power")
    dst: str = Field(description="region receiving power")
    amount: int = Field(description="megawatts to move")


class Plan(BaseModel):
    transfers: list[Transfer]


SYSTEM = """You balance a power grid. You get SHORT regions (need power) and
SURPLUS regions (spare power). Decide transfers to cover shortages.

FOLLOW THIS EXACT PROCEDURE:
1. Sort the short regions from BIGGEST shortage to smallest.
2. Take the biggest shortage first. FULLY cover it using available surplus
   before you give ANY power to the next region.
3. Only after it is fully covered (or surplus runs out) move to the next
   biggest shortage with whatever surplus is left.
4. Never send more than a surplus region actually has.
5. Do NOT split surplus evenly or "fairly" between regions. Priority order
   is strict: biggest shortage is served in full first.

WORKED EXAMPLE:
SHORT: A needs 200, B needs 300.  SURPLUS: C has 400.
Correct answer: C -> B 300 (B is bigger, cover it fully first),
then C -> A 100 (only 100 surplus left).
WRONG answer: C -> A 200, C -> B 200 (this is even-splitting -- never do this).
"""


def coordinator(state: GridState) -> dict:
    reports = state["reports"]

    shorts = [r for r in reports if r["status"] == "short"]
    surplus = [r for r in reports if r["status"] == "surplus"]

    if not shorts or not surplus:
        return {"plan": []}

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    planner = llm.with_structured_output(Plan)

    situation = f"SHORT regions: {shorts}\nSURPLUS regions: {surplus}"
    result = planner.invoke([("system", SYSTEM), ("human", situation)])

    plan = [(t.src, t.dst, t.amount) for t in result.transfers]
    return {"plan": plan}
