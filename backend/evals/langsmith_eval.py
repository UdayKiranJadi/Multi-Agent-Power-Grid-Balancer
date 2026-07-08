"""LangSmith eval for the PRODUCTION national coordinator.

Unlike run_eval.py (which scores the legacy flat coordinator with exact-match),
this scores src.national_coordinator.match_residuals -- the real LLM decision in
the deployed hierarchy -- against a versioned LangSmith dataset, using
property-based evaluators (not just brittle set-equality).

Modes:
  * LANGSMITH_API_KEY set   -> creates/loads a dataset and runs langsmith.evaluate(),
                               so results land in the LangSmith UI as an experiment.
  * LANGSMITH_API_KEY unset -> runs the same evaluators locally and prints a table,
                               so it still works offline / in CI with no upload.

Either way the coordinator itself needs OPENAI_API_KEY (it makes an LLM call).

Run:  python -m evals.langsmith_eval
"""

import os
from collections import defaultdict

from dotenv import load_dotenv
load_dotenv()

from src.national_coordinator import match_residuals
from evals.test_cases import NATIONAL_CASES

DATASET_NAME = "power-grid-national-coordinator"


def coordinator_matches(residuals: dict, planner=None) -> list[list]:
    """Run the coordinator, normalize matches to JSON-friendly [src, dst, amount]."""
    return [list(m) for m in match_residuals(residuals, planner=planner)]


def run_coordinator(inputs: dict) -> dict:
    """LangSmith target: dataset input -> coordinator output."""
    return {"matches": coordinator_matches(inputs["residuals"])}


# ---------------------------------------------------------------------------
# Evaluators. Each takes some of (inputs, outputs, reference_outputs) -- the
# LangSmith SDK inspects the parameter names -- and returns {key, score}.
# We call them with the same kwargs in offline mode, so there is ONE source of
# truth for "what correct means."
# ---------------------------------------------------------------------------

def _as_set(matches):
    return {tuple(m) for m in matches}


def exact_match(outputs, reference_outputs):
    """Did the coordinator produce exactly the expected matches?"""
    score = _as_set(outputs["matches"]) == _as_set(reference_outputs["matches"])
    return {"key": "exact_match", "score": bool(score)}


def no_invalid_transfers(inputs, outputs):
    """Every transfer: distinct regions, positive amount, from a real surplus to
    a real short. This is the 'code guarantees correctness' contract."""
    residuals = inputs["residuals"]
    shorts = {r for r, v in residuals.items() if v < 0}
    surplus = {r for r, v in residuals.items() if v > 0}
    ok = all(
        s != d and a > 0 and s in surplus and d in shorts
        for s, d, a in outputs["matches"]
    )
    return {"key": "no_invalid_transfers", "score": bool(ok)}


def respects_surplus(inputs, outputs):
    """No surplus region sends more than it actually has."""
    residuals = inputs["residuals"]
    sent = defaultdict(int)
    for s, d, a in outputs["matches"]:
        sent[s] += a
    ok = all(sent[r] <= residuals.get(r, 0) for r in sent)
    return {"key": "respects_surplus", "score": bool(ok)}


def covers_biggest_first(inputs, outputs):
    """The single biggest shortage must be covered up to the surplus available --
    this is the priority rule the prompt encodes (no even-splitting)."""
    residuals = inputs["residuals"]
    shorts = sorted([(r, v) for r, v in residuals.items() if v < 0], key=lambda x: x[1])
    if not shorts:
        return {"key": "covers_biggest_first", "score": True}
    biggest, need = shorts[0][0], -shorts[0][1]
    total_surplus = sum(v for v in residuals.values() if v > 0)
    received = sum(a for s, d, a in outputs["matches"] if d == biggest)
    return {"key": "covers_biggest_first", "score": received >= min(need, total_surplus)}


EVALUATORS = [exact_match, no_invalid_transfers, respects_surplus, covers_biggest_first]


# ---------------------------------------------------------------------------
# Modes
# ---------------------------------------------------------------------------

def run_langsmith():
    from langsmith import Client, evaluate

    client = Client()
    if not client.has_dataset(dataset_name=DATASET_NAME):
        ds = client.create_dataset(
            DATASET_NAME,
            description="National coordinator: regional residuals -> surplus/short matches.",
        )
        client.create_examples(
            dataset_id=ds.id,
            inputs=[{"residuals": c["residuals"]} for c in NATIONAL_CASES],
            outputs=[{"matches": [list(m) for m in c["expected"]]} for c in NATIONAL_CASES],
        )
        print(f"Created dataset '{DATASET_NAME}' with {len(NATIONAL_CASES)} examples.")
    else:
        print(f"Using existing dataset '{DATASET_NAME}'.")

    evaluate(
        run_coordinator,
        data=DATASET_NAME,
        evaluators=EVALUATORS,
        experiment_prefix="national-coordinator",
    )
    print("Experiment uploaded -- open the dataset in LangSmith to compare runs.")


def run_offline(planner=None):
    cols = ["exact_match", "no_invalid_transfers", "respects_surplus", "covers_biggest_first"]
    print(f"{'case':22} " + " ".join(f"{c:>20}" for c in cols))
    print("-" * (22 + 21 * len(cols)))

    agg = defaultdict(int)
    for case in NATIONAL_CASES:
        inputs = {"residuals": case["residuals"]}
        outputs = {"matches": coordinator_matches(case["residuals"], planner=planner)}
        reference_outputs = {"matches": [list(m) for m in case["expected"]]}

        results = {
            "exact_match": exact_match(outputs, reference_outputs)["score"],
            "no_invalid_transfers": no_invalid_transfers(inputs, outputs)["score"],
            "respects_surplus": respects_surplus(inputs, outputs)["score"],
            "covers_biggest_first": covers_biggest_first(inputs, outputs)["score"],
        }
        for k, v in results.items():
            agg[k] += int(v)
        cells = " ".join(f"{'PASS' if results[c] else 'FAIL':>20}" for c in cols)
        print(f"{case['name']:22} {cells}")

    n = len(NATIONAL_CASES)
    print("-" * (22 + 21 * len(cols)))
    totals = " ".join(f"{f'{agg[c]}/{n}':>20}" for c in cols)
    print(f"{'TOTAL':22} {totals}")


def main():
    if os.getenv("LANGSMITH_API_KEY"):
        run_langsmith()
    else:
        print("LANGSMITH_API_KEY not set -- running evaluators locally (no upload).\n")
        run_offline()


if __name__ == "__main__":
    main()
