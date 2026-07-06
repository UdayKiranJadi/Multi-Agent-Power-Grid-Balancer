"""Our exam: test cases + the answer key (from a simple trusted rule)."""

# Each case climbs in difficulty: sanity check -> edge case -> judgment call.
TEST_CASES = [
    {
        "name": "sanity_check",
        "regions": {"A": 0, "B": -200, "C": 300},   # negative = short, positive = surplus
        "expected": [("C", "B", 200)],
    },
    {
        "name": "not_enough_surplus",
        "regions": {"A": 0, "B": -400, "C": 100},
        "expected": [("C", "B", 100)],              # give what you can
    },
    {
        "name": "judgment_call",
        "regions": {"A": -200, "B": -300, "C": 400},
        "expected": [("C", "B", 300), ("C", "A", 100)],  # biggest shortage first
    },
]