HEAVY_SET = {0, 1, 3, 4, 7, 8, 9}


def extract_heavy_digits(draw: list[int]) -> list[int]:
    """
    Extract heavy digits from a draw.
    """
    return [d for d in draw if d in HEAVY_SET]
