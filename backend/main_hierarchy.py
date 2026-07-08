"""Entry point: run the HIERARCHICAL balancer on one hour of real data."""

from dotenv import load_dotenv
load_dotenv()

from src.data_loader import load_grid_data, get_hour
from src.hierarchy import run_hierarchy


def main():
    df = load_grid_data("data/grid.csv")
    hour = get_hour(df, "2024-01-01T00")

    result = run_hierarchy(hour)

    print("LOCAL transfers (within regions):")
    for s, d, a in result["local_transfers"]:
        print(f"  {s} -> {d}: {a} MW")

    print("\nRESIDUALS (net per region):")
    for reg, v in sorted(result["residuals"].items()):
        print(f"  {reg}: {v:+d} MW")

    print("\nNATIONAL transfers (between regions):")
    for s, d, a in result["national_transfers"]:
        print(f"  {s} -> {d}: {a} MW")


if __name__ == "__main__":
    main()