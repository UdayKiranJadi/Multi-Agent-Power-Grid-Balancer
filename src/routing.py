"""Multi-hop routing: find how power can flow between distant regions,
hopping through intermediate neighbors (BFS shortest path on the grid graph).
"""

from collections import deque
from src.regions import REGION_NEIGHBORS


def find_path(src: str, dst: str) -> list[str] | None:
    """Shortest chain of bordering regions from src to dst (BFS).

    Returns the list of regions to hop through, or None if unreachable.
    e.g. find_path("MIDA", "CAL") -> ["MIDA", "MIDW", "CENT", "SW", "CAL"]
    """
    if src == dst:
        return [src]

    queue = deque([[src]])          # queue of paths-so-far
    seen = {src}

    while queue:
        path = queue.popleft()
        node = path[-1]
        for neighbor in REGION_NEIGHBORS.get(node, ()):
            if neighbor == dst:
                return path + [neighbor]     # found the shortest path
            if neighbor not in seen:
                seen.add(neighbor)
                queue.append(path + [neighbor])
    return None                     # no path exists