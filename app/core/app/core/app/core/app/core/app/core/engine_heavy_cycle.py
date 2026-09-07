HEAVY_CYCLE = [1, 4, 7, 8, 9, 0, 3]


def next_heavy(current: int) -> int:
    """
    Get the next heavy digit in the cycle.
    """
    idx = HEAVY_CYCLE.index(current)
    return HEAVY_CYCLE[(idx + 1) % len(HEAVY_CYCLE)]
