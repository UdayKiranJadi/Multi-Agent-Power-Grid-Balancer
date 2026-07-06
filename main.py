"""Entry point: run one balancing cycle on a single hour of data."""

from src.data_loader import load_grid_data, get_hour
from src.graph import build_graph
from dotenv import load_dotenv
load_dotenv()

def main():
    app = build_graph()                          # real LLM coordinator
    df = load_grid_data("data/grid_sample.csv")  # swap for data/grid.csv once fetched
    hour = get_hour(df, "2024-01-01T00")

    result = app.invoke({"hour": hour, "reports": [], "plan": []})

    print("Region reports:")
    for r in result["reports"]:
        print(f"  {r['region']}: {r['status']} ({r['gap']:+d} MW)")

    print("\nReroute plan:")
    for src, dst, amt in result["plan"]:
        print(f"  {src} -> {dst}: {amt} MW")


if __name__ == "__main__":
    main()