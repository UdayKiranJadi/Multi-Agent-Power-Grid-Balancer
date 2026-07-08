"""Runs the coordinator on every test case and prints the score."""

from src.coordinator import coordinator
from evals.test_cases import TEST_CASES
from dotenv import load_dotenv
load_dotenv()

def gaps_to_reports(regions: dict) -> list[dict]:
    """Turn a test case's {region: gap} into the reports the coordinator reads."""
    reports = []
    for name, gap in regions.items():
        status = "short" if gap < 0 else "surplus" if gap > 0 else "ok"
        reports.append({"region": name, "gap": gap, "status": status})
    return reports


def run(coordinator_fn=coordinator) -> None:
    correct = 0
    for case in TEST_CASES:
        reports = gaps_to_reports(case["regions"])
        plan = coordinator_fn({"reports": reports})["plan"]

        got = {tuple(t) for t in plan}
        want = set(case["expected"])
        ok = got == want
        correct += ok
        print(f"  {case['name']:20} {'PASS' if ok else 'FAIL'}   got={sorted(got)}  want={sorted(want)}")

    n = len(TEST_CASES)
    print(f"\n  Accuracy: {correct}/{n} = {correct/n:.0%}")


if __name__ == "__main__":
    run()