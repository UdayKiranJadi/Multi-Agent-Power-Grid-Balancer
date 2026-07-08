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


# Cases for the PRODUCTION national coordinator (src.national_coordinator).
# These use REAL EIA region codes (not A/B/C), because that coordinator matches
# real regions. `residuals`: negative = short, positive = surplus. `expected` is
# the region-to-region match (pre-routing) the coordinator should produce.
NATIONAL_CASES = [
    {
        "name": "sanity_check",
        "residuals": {"CAL": -200, "SW": 300},
        "expected": [("SW", "CAL", 200)],
    },
    {
        "name": "not_enough_surplus",
        "residuals": {"CAL": -400, "SW": 100},
        "expected": [("SW", "CAL", 100)],                # give what you can
    },
    {
        "name": "judgment_call",
        "residuals": {"CAL": -200, "NW": -300, "SW": 500},
        "expected": [("SW", "NW", 300), ("SW", "CAL", 200)],  # biggest shortage first
    },
    {
        "name": "no_surplus",
        "residuals": {"CAL": -200, "NW": -300},
        "expected": [],                                  # nothing to move
    },
    {
        "name": "two_sources_priority",
        "residuals": {"MIDA": -500, "SE": 300, "MIDW": 300},
        "expected": [("SE", "MIDA", 300), ("MIDW", "MIDA", 200)],  # cover the big short
    },
]