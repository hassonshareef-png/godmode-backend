MIRROR_MAP = {
    0: 5,
    1: 6,
    2: 7,
    3: 8,
    4: 9,
    5: 0,
    6: 1,
    7: 2,
    8: 3,
    9: 4,
}


def mirror_digit(d: int) -> int:
    """
    Return the mirror of a digit using your mirror family.
    """
    return MIRROR_MAP[d]


def is_shadow_4_to_9(d: int) -> bool:
    """
    Check if digit is 4 (shadow of 9 in your logic).
    """
    return d == 4
