import itertools
from apscheduler.schedulers.background import BackgroundScheduler
import datetime

# ============================================================
#  NEW MEXICO NIGHT ENGINE
# ============================================================

def classify_digit(d):
    if d in [7, 8, 9]:
        return "high"
    if d in [0, 1, 2]:
        return "low"
    return "mid"

def move_digit(d, digit_type):
    moves = set()
    if digit_type == "high":
        moves.update([(d - 1) % 10, (d - 2) % 10, (d - 3) % 10])
    elif digit_type == "low":
        moves.update([(d + 1) % 10, (d + 2) % 10, (d + 3) % 10])
    elif digit_type == "mid":
        moves.update([(d + 1) % 10, (d - 1) % 10, (d + 2) % 10, (d - 2) % 10])
    return moves

def apply_month_math(d, month):
    return {(d + month) % 10, (d - month) % 10}

def apply_day_math(d, day):
    return {(d + day) % 10, (d - day) % 10}

def nm_position_filter(pos, digit):
    if pos == 1:
        return digit in [3, 4, 5, 6]
    if pos == 2:
        return digit in [3, 4, 5, 6, 7, 8]
    if pos == 3:
        return digit in [3, 4, 5, 6, 7, 8]
    return False

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

# ============================================================
#  FASTAPI ENDPOINT (IMPORT THIS ROUTER IN main.py)
# ============================================================

def nm_night_api(last_draw: str, month: int, day: int):
    results = nm_night_predict(last_draw, month, day)
    return {
        "state": "New Mexico",
        "mode": "Night",
        "last_draw": last_draw,
        "month": month,
        "day": day,
        "count": len(results),
        "results": results
    }

# ============================================================
#  AUTO-UPDATE SCHEDULER
# ============================================================

def update_nm_night():
    today = datetime.datetime.now()
    month = today.month
    day = today.day

    # Replace with your real last-night draw fetch
    last_draw = "502"

    results = nm_night_predict(last_draw, month, day)
    print("Auto-update NM Night:", results[:10])

scheduler = BackgroundScheduler()
scheduler.add_job(update_nm_night, "cron", hour=23, minute=59)
scheduler.start()

# ============================================================
#  NM VS ARKANSAS COMPARISON MODULE
# ============================================================

def compare_states():
    return {
        "New Mexico": {
            "pattern": "Math-cycle",
            "night_behavior": "Month/day math, high-drop, low-rise",
            "tools": ["NM Night Engine", "Month Math", "Day Math"],
            "predictability": "Medium"
        },
        "Arkansas": {
            "pattern": "Mirror/Flip",
            "night_behavior": "Heavy mirrors, flips, repeats",
            "tools": ["317", "123", "238", "713", "001"],
            "predictability": "High"
        }
    }

# ============================================================
#  MULTI-STATE NIGHT ANALYZER
# ============================================================

def analyze_state_night_pattern(draws):
    mirror = 0
    flip = 0
    math = 0

    for prev, curr in zip(draws, draws[1:]):
        for a, b in zip(prev, curr):
            if abs(int(a) - int(b)) == 5:
                mirror += 1
            if abs(int(a) - int(b)) == 1:
                flip += 1
            if abs(int(a) - int(b)) in [2,3,4,6,7,8,9]:
                math += 1

    total = mirror + flip + math

    return {
        "mirror_rate": mirror / total,
        "flip_rate": flip / total,
        "math_rate": math / total,
        "classification": (
            "Mirror-night" if mirror > flip and mirror > math else
            "Flip-night" if flip > mirror and flip > math else
            "Math-night"
        )
    }

# ============================================================
#  OPTIONAL: QUICK TEST
# ============================================================

if __name__ == "__main__":
    print("NM Night Test:", nm_night_predict("502", 8, 6)[:10])
    print("State Comparison:", compare_states())
    print("Analyzer:", analyze_state_night_pattern(["502","991","069","753","010","371"]))

    month = 8
    day = 6

    picks = nm_night_predict(last_night, month, day)
    print("NM Night Predictions:", picks[:20])
