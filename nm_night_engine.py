import itertools

# -----------------------------
# CLASSIFY DIGIT TYPE
# -----------------------------
def classify_digit(d):
    if d in [7, 8, 9]:
        return "high"
    if d in [0, 1, 2]:
        return "low"
    return "mid"

# -----------------------------
# MOVEMENT RULES (NM NIGHT)
# -----------------------------
def move_digit(d, digit_type):
    moves = set()

    # High digits DROP
    if digit_type == "high":
        moves.update([(d - 1) % 10, (d - 2) % 10, (d - 3) % 10])

    # Low digits RISE
    elif digit_type == "low":
        moves.update([(d + 1) % 10, (d + 2) % 10, (d + 3) % 10])

    # Mid digits SHIFT slightly
    elif digit_type == "mid":
        moves.update([(d + 1) % 10, (d - 1) % 10, (d + 2) % 10, (d - 2) % 10])

    return moves

# -----------------------------
# MONTH MATH (NM NIGHT)
# -----------------------------
def apply_month_math(d, month):
    return {(d + month) % 10, (d - month) % 10}

# -----------------------------
# DAY MATH (NM NIGHT)
# -----------------------------
def apply_day_math(d, day):
    return {(d + day) % 10, (d - day) % 10}

# -----------------------------
# POSITION FILTER (NM NIGHT)
# -----------------------------
def nm_position_filter(pos, digit):
    # NM night position rules:
    # pos1 → mid only
    # pos2 → mid/high
    # pos3 → mid/high

    if pos == 1:
        return digit in [3, 4, 5, 6]

    if pos == 2:
        return digit in [3, 4, 5, 6, 7, 8]

    if pos == 3:
        return digit in [3, 4, 5, 6, 7, 8]

    return False

# -----------------------------
# MAIN NM NIGHT ENGINE
# -----------------------------
def nm_night_predict(last_draw, month, day):
    digits = [int(x) for x in last_draw]

    pools = []

    for i, d in enumerate(digits):
        dtype = classify_digit(d)

        base_moves = move_digit(d, dtype)
        month_moves = apply_month_math(d, month)
        day_moves = apply_day_math(d, day)

        combined = base_moves | month_moves | day_moves

        filtered = [x for x in combined if nm_position_filter(i+1, x)]
        pools.append(filtered)

    combos = set()

    for a, b, c in itertools.product(pools[0], pools[1], pools[2]):
        combos.add(f"{a}{b}{c}")

    return sorted(combos)

# -----------------------------
# EXAMPLE USAGE
# -----------------------------
if __name__ == "__main__":
    # Example: NM night draw on 8/6
    last_night = "502"
    month = 8
    day = 6

    picks = nm_night_predict(last_night, month, day)
    print("NM Night Predictions:", picks[:20])
