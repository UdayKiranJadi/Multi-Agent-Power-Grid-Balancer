"""Maps each individual operator (balancing authority) to its EIA region.

This is the hierarchy's backbone: operator -> region -> national.
Groupings follow EIA Form 930.
"""

REGION_NAMES = {
    "CAL": "California", "CAR": "Carolinas", "CENT": "Central",
    "FLA": "Florida",    "MIDA": "Mid-Atlantic", "MIDW": "Midwest",
    "NE": "New England", "NW": "Northwest",   "NY": "New York",
    "SE": "Southeast",   "SW": "Southwest",   "TEN": "Tennessee",
    "TEX": "Texas",
}

OPERATOR_TO_REGION = {
    "BANC": "CAL", "CISO": "CAL", "IID": "CAL", "LDWP": "CAL", "TIDC": "CAL",
    "CPLE": "CAR", "CPLW": "CAR", "DUK": "CAR", "SC": "CAR", "SCEG": "CAR", "YAD": "CAR",
    "SPA": "CENT", "SWPP": "CENT",
    "FMPP": "FLA", "FPC": "FLA", "FPL": "FLA", "GVL": "FLA", "HST": "FLA",
    "JEA": "FLA", "NSB": "FLA", "SEC": "FLA", "TAL": "FLA", "TEC": "FLA",
    "PJM": "MIDA",
    "AECI": "MIDW", "EEI": "MIDW", "LGEE": "MIDW", "MISO": "MIDW", "OVEC": "MIDW",
    "ISNE": "NE",
    "AVA": "NW", "AVRN": "NW", "BPAT": "NW", "CHPD": "NW", "DOPD": "NW",
    "GCPD": "NW", "GRID": "NW", "GWA": "NW", "IPCO": "NW", "NEVP": "NW",
    "NWMT": "NW", "PACE": "NW", "PACW": "NW", "PGE": "NW", "PSCO": "NW",
    "PSEI": "NW", "SCL": "NW", "TPWR": "NW", "WACM": "NW", "WAUW": "NW", "WWA": "NW",
    "NYIS": "NY",
    "AEC": "SE", "SEPA": "SE", "SOCO": "SE",
    "AZPS": "SW", "DEAA": "SW", "EPE": "SW", "GRIF": "SW", "GRMA": "SW",
    "HGMA": "SW", "PNM": "SW", "SRP": "SW", "TEPC": "SW", "WALC": "SW",
    "TVA": "TEN",
    "ERCO": "TEX",
}


def region_of(operator: str) -> str | None:
    """Return the region code for an operator, or None if unknown."""
    return OPERATOR_TO_REGION.get(operator)