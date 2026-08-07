import itertools
import datetime
from fastapi import FastAPI
from apscheduler.schedulers.background import BackgroundScheduler

app = FastAPI(
    title="GODMODE++ Backend",
    description="Pick 3 / Pick 4 Prediction Engine — NM Night, NM Day, Multi-State, Dashboard, Analyzer",
    version="1.1.0"
)

# ============================================================
#  NEW MEXICO NIGHT ENGINE (PICK 3)
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
#  NEW MEXICO DAY ENGINE (PICK 3)
# ============================================================

def nm_day_predict(last_draw):
    digits = [int(x) for x in last_draw]
    pools = []

    for d in digits:
        moves = {
            d,                     # repeats
            (d + 1) % 10,          # flip up
            (d - 1) % 10,          # flip down
            (d + 2) % 10,          # small rise
            (d - 2) % 10,          # small drop
        }

        # mid digits stay stable
        if d in [3, 4, 5, 6]:
            moves.add(d)

        pools.append(list(moves))

    combos = set()
    for a, b, c in itertools.product(*pools):
        combos.add(f"{a}{b}{c}")

    return sorted(combos)

# ============================================================
#  PICK 4 ENGINE
# ============================================================

def pick4_engine(last_draw):
    digits = [int(x) for x in last_draw]
    pools = []

    for d in digits:
        moves = {
            (d + 1) % 10,
            (d - 1) % 10,
            (d + 2) % 10,
            (d - 2) % 10,
            (d + 5) % 10,
            (d - 5) % 10
        }
        pools.append(list(moves))

    combos = set()
    for a, b, c, d in itertools.product(*pools):
        combos.add(f"{a}{b}{c}{d}")

    return sorted(combos)

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
#  NM VS ARKANSAS COMPARISON
# ============================================================

def compare_states():
    return {
        "New Mexico": {
            "pattern": "Math-cycle (Night) / Flip-Repeat (Day)",
            "night_behavior": "Month/day math, high-drop, low-rise",
            "day_behavior": "Repeats, flips, mid stability",
            "predictability": "Medium"
        },
        "Arkansas": {
            "pattern": "Mirror/Flip",
            "night_behavior": "Heavy mirrors, flips, repeats",
            "predictability": "High"
        }
    }

# ============================================================
#  DATABASE LOGGING HOOKS
# ============================================================

def log_to_db(table, data):
    print(f"[DB LOG] {table}: {data}")

# ============================================================
#  AUTO-UPDATE SCHEDULER
# ============================================================

def update_nm_night():
    today = datetime.datetime.now()
    month = today.month
    day = today.day

    last_draw = "502"  # replace with real fetch

    results = nm_night_predict(last_draw, month, day)
    log_to_db("nm_night", results[:10])
    print("Auto-update NM Night:", results[:10])

scheduler = BackgroundScheduler()
scheduler.add_job(update_nm_night, "cron", hour=23, minute=59)
scheduler.start()

# ============================================================
#  FASTAPI ROUTES
# ============================================================

@app.get("/nm/night")
def api_nm_night(last_draw: str, month: int, day: int):
    return nm_night_predict(last_draw, month, day)

@app.get("/nm/day")
def api_nm_day(last_draw: str):
    return nm_day_predict(last_draw)

@app.get("/pick4")
def api_pick4(last_draw: str):
    return pick4_engine(last_draw)

@app.get("/compare")
def api_compare():
    return compare_states()

@app.get("/analyze")
def api_analyze(draws: list[str]):
    return analyze_state_night_pattern(draws)

@app.get("/dashboard")
def api_dashboard():
    return {
        "nm_night": nm_night_predict("502", 8, 6)[:10],
        "nm_day": nm_day_predict("502")[:10],
        "pick4": pick4_engine("1234")[:10],
        "state_compare": compare_states()
    }

@app.get("/mobile")
def api_mobile():
    return {
        "title": "GODMODE++ Mobile",
        "nm_night": nm_night_predict("502", 8, 6)[:5],
        "nm_day": nm_day_predict("502")[:5],
        "pick4": pick4_engine("1234")[:5]
    }

# ============================================================
#  SERVER READY
# ============================================================

if __name__ == "__main__":
    print("GODMODE++ Backend Loaded")
