# ============================================================
# GODMODE++ Numerology Engine (Backend Module)
# ============================================================

from datetime import datetime

# ------------------------------------------------------------
# Digit Root + Numerology Core Functions
# ------------------------------------------------------------

def digit_root(n: int) -> int:
    """Reduce a number to its digit root (1–9)."""
    while n > 9:
        n = sum(int(d) for d in str(n))
    return n

def mirror(n: int) -> int:
    """Mirror digit root (10 - n)."""
    return 10 - n if n in range(1, 10) else n

def is_master(n: int) -> bool:
    """Master number check (1 or 10)."""
    return n in (1, 10)

# ------------------------------------------------------------
# Main Feature Engine
# ------------------------------------------------------------

def compute_numerology_features(draw_number: str, draw_date: datetime):
    """
    Compute DR1, DR2, mirrors, master flags, date sum, and BiasScore.
    draw_number: '1234'
    draw_date: datetime object
    """

    # Split into pairs
    p1 = int(draw_number[:2])
    p2 = int(draw_number[2:])

    # Digit roots
    dr1 = digit_root(p1)
    dr2 = digit_root(p2)

    # Date sum root
    date_sum = digit_root(draw_date.month + draw_date.day)

    # Mirrors
    dr1_m = mirror(dr1)
    dr2_m = mirror(dr2)

    # Master flags
    dr1_master = is_master(dr1)
    dr2_master = is_master(dr2)
    sum_dr = digit_root(dr1 + dr2)
    sum_dr_master = is_master(sum_dr)

    # Connections
    connects_date = (
        dr1 == date_sum or
        dr2 == date_sum or
        dr1_m == date_sum or
        dr2_m == date_sum
    )

    # BiasScore (Director Mode)
    bias_score = (
        int(connects_date) +
        int(dr1_master) +
        int(dr2_master) +
        int(sum_dr_master)
    )

    return {
        "Pair1": p1,
        "Pair2": p2,
        "DR1": dr1,
        "DR2": dr2,
        "DR1_Mirror": dr1_m,
        "DR2_Mirror": dr2_m,
        "DR1_Master": dr1_master,
        "DR2_Master": dr2_master,
        "SumDR": sum_dr,
        "SumDR_Master": sum_dr_master,
        "DateSum": date_sum,
        "ConnectsDate": connects_date,
        "BiasScore": bias_score
    }

# ------------------------------------------------------------
# Batch Processor (for DataFrames or Lists)
# ------------------------------------------------------------

def apply_numerology_to_records(records):
    """
    records: list of dicts with keys:
        - draw_number (str)
        - draw_date (datetime or ISO string)
    Returns list of dicts with numerology features added.
    """

    output = []

    for r in records:
        # Normalize date
        if isinstance(r["draw_date"], str):
            draw_date = datetime.fromisoformat(r["draw_date"])
        else:
            draw_date = r["draw_date"]

        features = compute_numerology_features(
            draw_number=r["draw_number"],
            draw_date=draw_date
        )

        output.append({**r, **features})

    return output

