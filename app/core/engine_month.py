def get_month_digit(month: int) -> int:
    """
    Return the month digit (reset digit) from a month number.
    Example: 7 -> 7, 11 -> 1
    """
    return month % 10
