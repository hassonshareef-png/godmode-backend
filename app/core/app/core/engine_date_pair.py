def front_pair_alignment(front_pair: tuple[int, int], date: int, month_digit: int) -> bool:
    """
    Check if front pair + date collapses to the month digit.
    """
    front_sum = (front_pair[0] + front_pair[1]) % 10
    date_digit = date % 10
    return (front_sum + date_digit) % 10 == month_digit


def back_pair_alignment(back_pair: tuple[int, int], month_digit: int) -> bool:
    """
    Check if back pair collapses to the month digit.
    """
    back_sum = (back_pair[0] + back_pair[1]) % 10
    return back_sum == month_digit
