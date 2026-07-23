###############################################
# GODMODE++ ALL-IN-ONE ENGINE
# FastAPI + Streamlit + Pick4 + Pick3 + Router
# Multi-state + DB logging + Auto-update
###############################################

from fastapi import FastAPI
from pydantic import BaseModel
import streamlit as st
import requests
import sqlite3
import datetime

############################################################
# STATE BEHAVIOR ENGINE (MULTI-STATE)
############################################################

class StateProfile:
    def __init__(self, name, mirror, date_use, pattern, chaos, repeat, uses_3175, shapes):
        self.name = name
        self.mirror = mirror
        self.date_use = date_use
        self.pattern = pattern
        self.chaos = chaos
        self.repeat = repeat
        self.uses_3175 = uses_3175
        self.shapes = shapes

STATE_PROFILES = {
    "MO": StateProfile("Missouri", 2, 2, 2, 1, 2, 2,
                       {"straight": 2, "l_shape": 2, "repeat": 2, "borrow": 2, "mirror": 1}),
    "NM": StateProfile("New Mexico", 2, 2, 2, 2, 2, 2,
                       {"straight": 2, "l_shape": 2, "repeat": 2, "borrow": 1, "mirror": 2}),
    "OH": StateProfile("Ohio", 1, 1, 2, 1, 2, 2,
                       {"straight": 2, "l_shape": 1, "repeat": 2, "borrow": 1, "mirror": 1}),
    "GA": StateProfile("Georgia", 1, 2, 2, 1, 2, 2,
                       {"straight": 2, "l_shape": 1, "repeat": 2, "borrow": 1, "mirror": 1}),
    "FL": StateProfile("Florida", 1, 2, 2, 1, 2, 2,
                       {"straight": 2, "l_shape": 1, "repeat": 2, "borrow": 1, "mirror": 1}),
    "TX": StateProfile("Texas", 1, 2, 2, 1, 2, 2,
                       {"straight": 2, "l_shape": 1, "repeat": 2, "borrow": 1, "mirror": 1}),
    "MI": StateProfile("Michigan", 2, 2, 2, 2, 2, 2,
                       {"straight": 2, "l_shape": 2, "repeat": 2, "borrow": 1, "mirror": 2}),
    "MD": StateProfile("Maryland", 2, 2, 2, 2, 2, 2,
                       {"straight": 2, "l_shape": 2, "repeat": 2, "borrow": 1, "mirror": 2}),
    "VA": StateProfile("Virginia", 2, 2, 2, 2, 2, 2,
                       {"straight": 2, "l_shape": 2, "repeat": 2, "borrow": 1, "mirror": 2}),
    "NC": StateProfile("North Carolina", 2, 2, 2, 1, 2, 2,
                       {"straight": 2, "l_shape": 2, "repeat": 2, "borrow": 1, "mirror": 2}),
    "SC": StateProfile("South Carolina", 2, 2, 2, 1, 2, 2,
                       {"straight": 2, "l_shape": 2, "repeat": 2, "borrow": 1, "mirror": 2}),
}

SUPPORTED_STATES = list(STATE_PROFILES.keys())

def get_state_profile(code):
    return STATE_PROFILES.get(code.upper())

def godmode_weights(code):
    p = get_state_profile(code)
    if not p:
        return {}
    return {
        "mirror_weight": p.mirror,
        "date_weight": p.date_use,
        "pattern_weight": p.pattern,
        "chaos_weight": p.chaos,
        "repeat_weight": p.repeat,
        "rundown_3175_weight": p.uses_3175,
        "shape_profile": p.shapes,
    }

############################################################
# SHAPE ENGINE
############################################################

def apply_shapes(engine, shape_profile):
    for shape, weight in shape_profile.items():
        engine.set_shape_weight(shape, weight)

def family_for_date_sum(date_sum):
    if date_sum == 5:
        return [5, 6]
    return [date_sum, (date_sum + 1) % 10]

############################################################
# RUNDOWN 3175
############################################################

BASE_3175 = [3, 1, 7, 5]

def run_3175(date_sum):
    return [(d + date_sum) % 10 for d in BASE_3175]

############################################################
# PICK 4 GENERATOR
############################################################

def generate_pick4(family, shapes, rundown_digits):
    out = set()

    if shapes.get("straight", 0) > 0:
        for a in family:
            for b in family:
                for c in family:
                    for d in family:
                        out.add(f"{a}{b}{c}{d}")

    if shapes.get("repeat", 0) > 0:
        for a in family:
            for b in family:
                out.add(f"{a}{a}{b}{a}")
                out.add(f"{a}{b}{a}{a}")

    if shapes.get("borrow", 0) > 0 and rundown_digits:
        for a in family:
            for b in rundown_digits:
                out.add(f"{a}{b}{a}{b}")
                out.add(f"{b}{a}{b}{a}")

    return sorted(out)

############################################################
# PICK 3 GENERATOR
############################################################

def generate_pick3(family, shapes):
    out = set()

    if shapes.get("straight", 0) > 0:
        for a in family:
            for b in family:
                for c in family:
                    out.add(f"{a}{b}{c}")

    if shapes.get("repeat", 0) > 0:
        for a in family:
            out.add(f"{a}{a}{a}")
            for b in family:
                out.add(f"{a}{a}{b}")
                out.add(f"{a}{b}{a}")

    return sorted(out)

############################################################
# PICK 5 / PICK 6 GENERATORS
############################################################

def generate_pick5(family, shapes):
    out = set()
    if shapes.get("straight", 0) > 0:
        for a in family:
            for b in family:
                for c in family:
                    for d in family:
                        for e in family:
                            out.add(f"{a}{b}{c}{d}{e}")
    return sorted(out)

def generate_pick6(family, shapes):
    out = set()
    if shapes.get("straight", 0) > 0:
        for a in family:
            for b in family:
                for c in family:
                    for d in family:
                        for e in family:
                            for f in family:
                                out.add(f"{a}{b}{c}{d}{e}{f}")
    return sorted(out)

############################################################
# DIRECTOR MODES
############################################################

class SimpleEngine:
    def __init__(self):
        self.shape_weights = {}

    def set_shape_weight(self, shape, weight):
        self.shape_weights[shape] = weight

def get_date_sum(day):
    return sum(int(d) for d in str(day)) % 10

def director_mode_pick4(state_code, day):
    weights = godmode_weights(state_code)
    if not weights:
        return []

    date_sum = get_date_sum(day)
    family = family_for_date_sum(date_sum)

    engine = SimpleEngine()
    apply_shapes(engine, weights["shape_profile"])

    rundown_digits = []
    if weights["rundown_3175_weight"] >= 1:
        rundown_digits = run_3175(date_sum)

    return generate_pick4(family, engine.shape_weights, rundown_digits)

def director_mode_pick3(state_code, day):
    weights = godmode_weights(state_code)
    if not weights:
        return []

    date_sum = get_date_sum(day)
    family = family_for_date_sum(date_sum)

    engine = SimpleEngine()
    apply_shapes(engine, weights["shape_profile"])

    return generate_pick3(family, engine.shape_weights)

def director_mode_pick5(state_code, day):
    weights = godmode_weights(state_code)
    if not weights:
        return []

    date_sum = get_date_sum(day)
    family = family_for_date_sum(date_sum)

    engine = SimpleEngine()
    apply_shapes(engine, weights["shape_profile"])

    return generate_pick5(family, engine.shape_weights)

def director_mode_pick6(state_code, day):
    weights = godmode_weights(state_code)
    if not weights:
        return []

    date_sum = get_date_sum(day)
    family = family_for_date_sum(date_sum)

    engine = SimpleEngine()
    apply_shapes(engine, weights["shape_profile"])

    return generate_pick6(family, engine.shape_weights)

############################################################
# MULTI-STATE ROUTERS
############################################################

def route_state_pick4(state, day):
    if state.upper() not in SUPPORTED_STATES:
        return []
    return director_mode_pick4(state, day)

def route_state_pick3(state, day):
    if state.upper() not in SUPPORTED_STATES:
        return []
    return director_mode_pick3(state, day)

def route_state_pick5(state, day):
    if state.upper() not in SUPPORTED_STATES:
        return []
    return director_mode_pick5(state, day)

def route_state_pick6(state, day):
    if state.upper() not in SUPPORTED_STATES:
        return []
    return director_mode_pick6(state, day)

############################################################
# GODMODE++ UNIFIED ENGINE
############################################################

def godmode_predict(state, day):
    return {
        "state": state.upper(),
        "day": day,
        "pick4": route_state_pick4(state, day),
        "pick3": route_state_pick3(state, day),
        "pick5": route_state_pick5(state, day),
        "pick6": route_state_pick6(state, day),
    }

############################################################
# SIMPLE DB LOGGING (SQLite)
############################################################

DB_PATH = "godmode_history.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT,
            state TEXT,
            day INTEGER,
            game TEXT,
            numbers TEXT
        )
    """)
    conn.commit()
    conn.close()

def log_predictions(state, day, game, numbers):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    ts = datetime.datetime.utcnow().isoformat()
    for n in numbers:
        c.execute(
            "INSERT INTO predictions (ts, state, day, game, numbers) VALUES (?, ?, ?, ?, ?)",
            (ts, state.upper(), day, game, n),
        )
    conn.commit()
    conn.close()

############################################################
# AUTO-UPDATE STUB (RESULTS HOOK)
############################################################

def auto_update_from_results(state, game, winning_numbers):
    # Stub: you can later wire real result feeds here.
    # For now, just print that an update would happen.
    print(f"[AUTO-UPDATE] State={state}, Game={game}, Winning={winning_numbers}")
    # Here you could adjust weights, shapes, etc.

############################################################
# FASTAPI BACKEND (FULL SUITE)
############################################################

app = FastAPI(title="GODMODE++ API")

class PredictionRequest(BaseModel):
    state: str
    day: int

class ResultUpdate(BaseModel):
    state: str
    game: str
    winning_numbers: list[str]

@app.on_event("startup")
def startup_event():
    init_db()

@app.get("/states")
def list_states():
    return {"states": SUPPORTED_STATES}

@app.post("/predict/pick4")
def predict_pick4(req: PredictionRequest):
    preds = route_state_pick4(req.state, req.day)
    log_predictions(req.state, req.day, "pick4", preds)
    return {"state": req.state.upper(), "day": req.day, "predictions": preds}

@app.post("/predict/pick3")
def predict_pick3(req: PredictionRequest):
    preds = route_state_pick3(req.state, req.day)
    log_predictions(req.state, req.day, "pick3", preds)
    return {"state": req.state.upper(), "day": req.day, "predictions": preds}

@app.post("/predict/pick5")
def predict_pick5(req: PredictionRequest):
    preds = route_state_pick5(req.state, req.day)
    log_predictions(req.state, req.day, "pick5", preds)
    return {"state": req.state.upper(), "day": req.day, "predictions": preds}

@app.post("/predict/pick6")
def predict_pick6(req: PredictionRequest):
    preds = route_state_pick6(req.state, req.day)
    log_predictions(req.state, req.day, "pick6", preds)
    return {"state": req.state.upper(), "day": req.day, "predictions": preds}

@app.post("/predict/godmode")
def predict_godmode(req: PredictionRequest):
    data = godmode_predict(req.state, req.day)
    log_predictions(req.state, req.day, "pick4", data["pick4"])
    log_predictions(req.state, req.day, "pick3", data["pick3"])
    log_predictions(req.state, req.day, "pick5", data["pick5"])
    log_predictions(req.state, req.day, "pick6", data["pick6"])
    return data

@app.post("/results/update")
def update_results(req: ResultUpdate):
    auto_update_from_results(req.state, req.game, req.winning_numbers)
    return {"status": "ok"}

############################################################
# STREAMLIT FRONTEND (FULL UI)
############################################################

def streamlit_ui():
    st.set_page_config(page_title="GODMODE++", layout="wide")
    st.title("GODMODE++ Lottery Engine")

    col1, col2 = st.columns(2)
    with col1:
        state = st.selectbox("State", SUPPORTED_STATES, index=SUPPORTED_STATES.index("MO"))
        day = st.number_input("Day number", min_value=1, max_value=366, value=23)
    with col2:
        st.write("Games: Pick 3, Pick 4, Pick 5, Pick 6")
        st.write("Backend: FastAPI")
        st.write("Logging: SQLite")

    tabs = st.tabs(["GODMODE", "Pick 4", "Pick 3", "Pick 5", "Pick 6"])

    payload = {"state": state, "day": int(day)}

    if st.button("Run GODMODE++"):
        resp = requests.post("http://localhost:8000/predict/godmode", json=payload)
        if resp.status_code == 200:
            data = resp.json()

            with tabs[0]:
                st.subheader(f"GODMODE++ ({data['state']}, day {data['day']})")
                st.write("Pick 4 (top 50):")
                for p in data["pick4"][:50]:
                    st.write(p)
                st.write("Pick 3 (top 50):")
                for p in data["pick3"][:50]:
                    st.write(p)

            with tabs[1]:
                st.subheader("Pick 4")
                for p in data["pick4"][:100]:
                    st.write(p)

            with tabs[2]:
                st.subheader("Pick 3")
                for p in data["pick3"][:100]:
                    st.write(p)

            with tabs[3]:
                st.subheader("Pick 5")
                for p in data["pick5"][:50]:
                    st.write(p)

            with tabs[4]:
                st.subheader("Pick 6")
                for p in data["pick6"][:50]:
                    st.write(p)
        else:
            st.error("API error. Make sure FastAPI is running on localhost:8000")

############################################################
# MAIN ENTRY
############################################################

if __name__ == "__main__":
    print("Run FastAPI with:")
    print("  uvicorn godmode_all_in_one:app --reload")
    print("Run Streamlit with:")
    print("  streamlit run godmode_all_in_one.py")
    # To use Streamlit UI, uncomment below:
    # streamlit_ui()
