def reduce_digit(n: int) -> int:
    """
    Reduce a number to a single digit by repeated digit sum.
    Example: 17 -> 8, 13 -> 4
    """
    while n > 9:
        n = sum(int(d) for d in str(n))
    return n


def pair_sum(a: int, b: int) -> int:
    """
    Sum two digits and reduce to a single digit.
    """
    return reduce_digit(a + b)
