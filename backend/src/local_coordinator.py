"""Local coordinator: balance operators WITHIN one region, escalate the leftover."""


def balance_region(reports: list[dict]) -> tuple[list[tuple], int]:
    """Balance operators inside ONE region.

    Returns (transfers, residual). residual < 0 = region still short (escalate);
    residual > 0 = region has spare to offer up.
    """
    shorts = sorted([r for r in reports if r["gap"] < 0],
                    key=lambda r: r["gap"])
    surplus = [{"op": r["region"], "have": r["gap"]}
               for r in reports if r["gap"] > 0]
    surplus.sort(key=lambda x: -x["have"])

    transfers = []
    for short in shorts:
        need = -short["gap"]
        for sp in surplus:
            if need <= 0:
                break
            if sp["have"] <= 0:
                continue
            move = min(need, sp["have"])
            transfers.append((sp["op"], short["region"], move))
            sp["have"] -= move
            need -= move

    residual = sum(r["gap"] for r in reports)
    return transfers, residual