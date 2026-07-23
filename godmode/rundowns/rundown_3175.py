BASE_3175 = [3, 1, 7, 5]

def run_3175(date_sum: int) -> list[int]:
    """
    Simple 3175 rundown: add date-sum to each digit mod 10.
    Example: date_sum=5 → 3175 + 5 = 8670
    """
    return [(d + date_sum) % 10 for d in BASE_3175]
