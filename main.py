"""Entry point: run one balancing cycle on a single hour of real data."""

from dotenv import load_dotenv
load_dotenv()

from src.data_loader import load_grid_data, get_hour
from src.graph import build_graph


def main():
    df = load_grid_data("data/grid.csv")          # real EIA data, all regions
    hour = get_hour(df, "2024-01-01T00")          # pick any hour in your data

    regions = list(hour.keys())                   # regions come from the data
    app = build_graph(regions)                    # graph built dynamically

    result = app.invoke({"hour": hour, "reports": [], "plan": []})

    shorts  = [r for r in result["reports"] if r["status"] == "short"]
    surplus = [r for r in result["reports"] if r["status"] == "surplus"]
    print(f"{len(regions)} regions | {len(shorts)} short, {len(surplus)} surplus\n")

    print("Reroute plan (top shortages covered first):")
    for src, dst, amt in result["plan"]:
        print(f"  {src} -> {dst}: {amt} MW")


if __name__ == "__main__":
    main()
