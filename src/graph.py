"""Wires the agents together with LangGraph (State + nodes + edges)."""

from langgraph.graph import StateGraph, START, END
from src.state import GridState
from src.region_agent import make_region_agent
from src.coordinator import coordinator




def build_graph(regions : list[str], coordinator_fn = coordinator):
    g = StateGraph(GridState)

    # NODES: one per region, plus the coordinator
    for name in regions:
        g.add_node(f"region_{name}", make_region_agent(name))
    g.add_node("coordinator", coordinator_fn)

    # EDGES: START fans out to every region, they fan back into coordinator
    for name in regions:
        g.add_edge(START, f"region_{name}")
        g.add_edge(f"region_{name}", "coordinator")
    g.add_edge("coordinator", END)

    return g.compile()