# main.py

from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional
import random

app = FastAPI()


# ===============================
# MODELS
# ===============================

class PickRequest(BaseModel):
    digits: str
    mode: Optional[str] = None


class DirectorRequest(BaseModel):
    overrideEarth: bool = False
    overrideUniverse: bool = False
    probabilityWeight: int = 50
    seed: Optional[str] = None


# ===============================
# HELPERS
# ===============================

def six_brings_nine(nums: List[int]) -> List[int]:
    if 6 in nums and 9 not in nums:
        nums.append(9)
    return nums


def digit_root(n: int) -> int:
    s = sum(int(d) for d in str(n))
    return s % 10


def mirror_number_40(n: int) -> int:
    return 40 - n


def get_earth_phase() -> str:
    phases = ["Opening", "Rising", "Peak", "Falling", "Reset"]
    return random.choice(phases)


def get_earth_drift() -> int:
    return random.choice([-2, -1, 0, 1, 2])


def build_unified_grids(digits: List[int], type_: str):
    s = sum(digits)
    root = s % 10

    if type_ == "P4":
        pairs8 = [digits[0] + digits[1], digits[2] + digits[3]]
        anchors5 = [digits[0], digits[3]]
        mini3 = [digits[1], digits[2]]
        final2 = [digits[2], digits[3]]
        base_ttt = digits[:3]
    else:
        pairs8 = [digits[0] + digits[1], digits[1] + digits[2]]
        anchors5 = [digits[0], digits[2]]
        mini3 = [digits[0], digits[1]]
        final2 = [digits[1], digits[2]]
        base_ttt = digits

    plus3 = [(d + 3) % 10 for d in base_ttt]
    plus6 = [(d + 6) % 10 for d in base_ttt]
    ttt = [
        [base_ttt[0], plus3[0], plus6[0]],
        [base_ttt[1], plus3[1], plus6[1]],
        [base_ttt[2], plus3[2], plus6[2]],
    ]

    grids = {
        "grid9": {"sum": s, "root": root},
        "grid8": {"pairs": pairs8},
        "grid7": {"mirrors": [9 - d for d in digits]},
        "grid6": {"drift": [d + 1 for d in digits]},
        "grid5": {"anchors": anchors5},
        "grid4": {"ticTacToe": ttt},
        "grid3": {"mini": mini3},
        "grid2": {"finalPair": final2},
    }
    return grids


def build_strategies(digits: List[int], type_: str) -> List[str]:
    s = sum(digits)
    if type_ == "P4":
        high_thresh = 20
        low_thresh = 10
    else:
        high_thresh = 15
        low_thresh = 7

    is_high = s >= high_thresh
    is_low = s <= low_thresh

    consecutive = (
        abs(digits[1] - digits[0]) == 1
        or abs(digits[-1] - digits[-2]) == 1
    )
    repeats = len(set(digits)) != len(digits)

    strategies = []
    if is_high:
        strategies.append("Use +9 Workout")
    if is_low:
        strategies.append("Use +3 Workout")
    if not is_high and not is_low:
        strategies.append("Use +6 Workout")

    if consecutive:
        strategies.append("1-Ups / 1-Downs")
    if repeats:
        strategies.append("Traveling Numbers")

    strategies.extend([
        "9-Grid Scan",
        "8-Grid Compression",
        "7-Grid Mirror",
        "6-Grid Drift",
        "5-Grid Anchors",
        "4-Grid Tic Tac Toe",
        "3-Grid Micro Pattern",
        "2-Grid Final Pair",
    ])

    return strategies


# ===============================
# QUICK PICK (6→9)
# ===============================

@app.get("/api/quickpick")
def quickpick():
    picks: List[int] = []
    while len(picks) < 5:
        n = random.randint(1, 39)
        if n not in picks:
            picks.append(n)

    picks = six_brings_nine(picks)
    picks = sorted(set(picks))
    return {"numbers": picks}


# ===============================
# GOD MODE RUNDOWN
# ===============================

GOD_LAST_DRAW = [7, 14, 22, 31, 36]


@app.get("/api/god-rundown")
def god_rundown():
    breakdown = []
    for n in GOD_LAST_DRAW:
        mirror = mirror_number_40(n)
        root = digit_root(n)
        specials = [root]
        specials = six_brings_nine(specials)
        anchors = []
        if 0 in specials:
            anchors.append(0)
        if 5 in specials:
            anchors.append(5)

        breakdown.append({
            "base": n,
            "mirror": mirror,
            "root": root,
            "specials": sorted(set(specials)),
            "anchors": anchors or ["none"],
        })

    lines = [
        f"#{item['base']} → mirror {item['mirror']}, "
        f"root {item['root']}, specials [{', '.join(map(str, item['specials']))}], "
        f"anchors [{', '.join(map(str, item['anchors']))}]"
        for item in breakdown
    ]
    return {"output": " | ".join(lines), "breakdown": breakdown}


# ===============================
# UNIVERSE MODE
# ===============================

@app.get("/api/universe")
def universe():
    # Simple universe summary using God rundown + quickpick
    god = god_rundown()
    qp = quickpick()
    text = (
        "Cosmic Universe Engine ACTIVE | "
        f"Rundown: {god['output']} | "
        f"Generator (6→9): [{', '.join(map(str, qp['numbers']))}]"
    )
    return {"output": text}


# ===============================
# DIRECTOR MODE
# ===============================

@app.post("/api/director")
def director(req: DirectorRequest):
    phase = get_earth_phase()
    drift = get_earth_drift()

    base = GOD_LAST_DRAW.copy()
    base = [n + drift for n in base]

    if req.seed:
        try:
            seed_num = int(req.seed)
        except ValueError:
            seed_num = 0
        base = [n + (seed_num % 10) for n in base]

    weight = req.probabilityWeight / 100.0
    base = [round(n * weight) for n in base]

    # clamp
    clamped = []
    for n in base:
        if n < 1:
            n = 1
        if n > 39:
            n = 39
        clamped.append(n)

    clamped = six_brings_nine(clamped)
    clamped = sorted(set(clamped))

    text = (
        f"Compiled Prediction → [{', '.join(map(str, clamped))}] | "
        f"Phase: {phase}, Drift: {drift}, "
        f"Weight: {req.probabilityWeight}%, Seed: {req.seed or 'none'}"
    )

    if req.overrideEarth:
        text += " | Earth override: ACTIVE"
    if req.overrideUniverse:
        text += " | Universe override: ACTIVE"

    return {
        "output": text,
        "numbers": clamped,
        "earthPhase": phase,
        "earthDrift": drift,
    }


# ===============================
# PICK 3 / PICK 4 ENGINES
# ===============================

@app.post("/api/pick3")
def pick3(req: PickRequest):
    digits = [int(d) for d in req.digits]
    if len(digits) != 3:
        return {"error": "Pick3 requires exactly 3 digits."}

    grids = build_unified_grids(digits, "P3")
    strategies = build_strategies(digits, "P3")

    strategy_text = f"Pick 3 Strategies → {' | '.join(strategies)}"
    ttt_rows = [" ".join(str(x) for x in row) for row in grids["grid4"]["ticTacToe"]]

    return {
        "strategies": strategies,
        "strategyText": strategy_text,
        "grid9": grids["grid9"],
        "grid8": grids["grid8"],
        "grid7": grids["grid7"],
        "grid6": grids["grid6"],
        "grid5": grids["grid5"],
        "grid4": {
            "ticTacToe": grids["grid4"]["ticTacToe"],
            "ticTacToeRows": ttt_rows,
        },
        "grid3": grids["grid3"],
        "grid2": grids["grid2"],
    }


@app.post("/api/pick4")
def pick4(req: PickRequest):
    digits = [int(d) for d in req.digits]
    if len(digits) != 4:
        return {"error": "Pick4 requires exactly 4 digits."}

    grids = build_unified_grids(digits, "P4")
    strategies = build_strategies(digits, "P4")

    strategy_text = f"Pick 4 Strategies → {' | '.join(strategies)}"
    ttt_rows = [" ".join(str(x) for x in row) for row in grids["grid4"]["ticTacToe"]]

    return {
        "strategies": strategies,
        "strategyText": strategy_text,
        "grid9": grids["grid9"],
        "grid8": grids["grid8"],
        "grid7": grids["grid7"],
        "grid6": grids["grid6"],
        "grid5": grids["grid5"],
        "grid4": {
            "ticTacToe": grids["grid4"]["ticTacToe"],
            "ticTacToeRows": ttt_rows,
        },
        "grid3": grids["grid3"],
        "grid2": grids["grid2"],
    }

