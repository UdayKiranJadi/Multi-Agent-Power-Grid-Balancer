"""One region agent: read -> compute gap -> decide status -> report."""

from src.state import GridState, RegionReport


def make_region_agent(region: str):
    """Build a LangGraph node for one region (same code, reused for all)."""

    def region_agent(state: GridState) -> dict:
        # 1. READ this region's numbers for the hour
        numbers = state["hour"][region]
        demand = numbers["demand"]
        supply = numbers["supply"]

        # 2. COMPUTE the gap  (plain math -- no LLM needed)
        gap = supply - demand

        # 3. DECIDE status   (simple thresholds -- also plain code, for now)
        if gap < 0:
            status = "short"
        elif gap > 0:
            status = "surplus"
        else:
            status = "ok"

        # 4. REPORT back -- appended into shared State (merged by operator.add)
        report: RegionReport = {"region": region, "gap": gap, "status": status}
        return {"reports": [report]}

    return region_agent