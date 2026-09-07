from app.core.engine_month import get_month_digit
from app.core.engine_date_pair import front_pair_alignment, back_pair_alignment
from app.core.engine_pairs import pair_sum
from app.core.engine_mirror import mirror_digit, is_shadow_4_to_9
from app.core.engine_heavy_cycle import next_heavy
from app.core.engine_night_reset import extract_heavy_digits


def analyze_draw(draw: str, date: int, month: int) -> dict:
    """
    Full Director Mode analysis for a single draw.
    """
    digits = [int(d) for d in draw]
    if len(digits) != 4:
        raise ValueError("Draw must be 4 digits.")

    front_pair = (digits[0], digits[1])
    back_pair = (digits[2], digits[3])

    month_digit = get_month_digit(month)

    front_ok = front_pair_alignment(front_pair, date, month_digit)
    back_ok = back_pair_alignment(back_pair, month_digit)

    front_sum = pair_sum(*front_pair)
    back_sum = pair_sum(*back_pair)

    front_mirror = mirror_digit(front_sum)
    back_mirror = mirror_digit(back_sum)

    heavy_digits = extract_heavy_digits(digits)

    # Optional: next heavy from month digit
    next_heavy_digit = next_heavy(month_digit) if month_digit in [1, 4, 7, 8, 9, 0, 3] else None

    return {
        "draw": draw,
        "date": date,
        "month": month,
        "month_digit": month_digit,
        "front_pair": front_pair,
        "back_pair": back_pair,
        "front_alignment_month": front_ok,
        "back_alignment_month": back_ok,
        "front_sum": front_sum,
        "back_sum": back_sum,
        "front_mirror": front_mirror,
        "back_mirror": back_mirror,
        "front_is_4_shadow": is_shadow_4_to_9(front_sum),
        "back_is_4_shadow": is_shadow_4_to_9(back_sum),
        "heavy_digits": heavy_digits,
        "next_heavy_from_month": next_heavy_digit,
    }
