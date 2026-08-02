from typing import List

def generate_pick4(family: List[int],
                   shapes: dict,
                   rundown_digits: List[int]) -> List[str]:
    """
    Very simple Pick 4 generator using:
    - family digits (e.g., [5, 6])
    - shape weights (straight/repeat/borrow/mirror)
    - optional rundown digits (from 3175)
    """
    out = set()

    # straight family
    if shapes.get("straight", 0) > 0:
        for a in family:
            for b in family:
                for c in family:
                    for d in family:
                        out.add(f"{a}{b}{c}{d}")

    # repeat patterns
    if shapes.get("repeat", 0) > 0:
        for a in family:
            for b in family:
                out.add(f"{a}{a}{b}{a}")
                out.add(f"{a}{b}{a}{a}")

    # borrow from rundown
    if shapes.get("borrow", 0) > 0 and rundown_digits:
        for a in family:
            for b in rundown_digits:
                out.add(f"{a}{b}{a}{b}")
                out.add(f"{b}{a}{b}{a}")

    return sorted(out)
