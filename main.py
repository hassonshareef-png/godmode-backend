from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

# -----------------------------------------
# IMPORT YOUR CORNER ENGINE
# -----------------------------------------
from services.corner_signal import analyze_draw_with_grid

app = FastAPI(
    title="GODMODE++ Backend",
    description="Prediction Engine API",
    version="1.0.0"
)

# ---------------------------
# CORS (Frontend Access)
# ---------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # GitHub Pages frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------
# MODELS
# ---------------------------
class LoginRequest(BaseModel):
    email: str
    password: str

class AnalyzeRequest(BaseModel):
    draw_id: str
    rundown_grid: List[List[str]]
    pick3_day: Optional[str] = None
    pick3_night: Optional[str] = None
    pick4: Optional[str] = None
    base_score: Optional[float] = 0.5
    alpha: Optional[float] = None

class Director3175Request(BaseModel):
    history: List[str]

# -----------------------------------------
# 3175 DIRECTOR MODE ENGINE
# -----------------------------------------
def run_3175_engine(draw_history):
    """
    Full 3175 Director Mode Engine
    """
    last_20 = draw_history[-20:]

    seed = [3, 1, 7, 5]

    mirror = {0:5,1:6,2:7,3:8,4:9,5:0,6:1,7:2,8:3,9:4}
    mirror_seed = [mirror[n] for n in seed]

    corner_pairs = [(3,1), (1,7), (7,5), (5,3)]

    hits = []
    for draw in last_20:
        nums = [int(n) for n in draw]

        if any(n in seed for n in nums):
            hits.append(("seed", draw))

        if any(n in mirror_seed for n in nums):
            hits.append(("mirror", draw))

        for a,b in corner_pairs:
            if a in nums and b in nums:
                hits.append(("corner", draw))

    return {
        "next_hot": seed,
        "next_mirror": mirror_seed,
        "corner_pairs": corner_pairs,
        "recent_hits": hits
    }

# -----------------------------------------
# DIRECTOR MODE ALERT LOGIC
# -----------------------------------------
def director_mode_3175_monitor(pred):
    hits = pred["recent_hits"]

    if hits:
        return {
            "alert": True,
            "level": "RED",
            "reason": hits
        }

    return {
        "alert": False,
        "level": "GREEN",
        "reason": []
    }

# -----------------------------------------
# AUTO UPDATE ENGINE
# -----------------------------------------
def auto_update_engine(draw_history):
    pred_3175 = run_3175_engine(draw_history)
    alert_3175 = director_mode_3175_monitor(pred_3175)

    return {
        "3175_prediction": pred_3175,
        "3175_alert": alert_3175
    }

# -----------------------------------------
# PREDICTION ENGINE HOOK
# -----------------------------------------
def prediction_engine(draw_history):
    p3175 = run_3175_engine(draw_history)

    return {
        "3175": p3175
    }

# ---------------------------
# ROOT + HEALTH
# ---------------------------
@app.get("/")
def root():
    return {"status": "GODMODE++ backend running"}

@app.get("/health")
def health():
    return {"ok": True}

# ---------------------------
# LOGIN ENDPOINT
# ---------------------------
@app.post("/login")
def login(req: LoginRequest):
    # TEMP: Replace with real DB later
    if req.email == "test@test.com" and req.password == "1234":
        return {"ok": True, "token": "godmode-token-001"}

    raise HTTPException(status_code=401, detail="Invalid credentials")

# ---------------------------
# PREDICTION ENDPOINT
# ---------------------------
@app.get("/predict")
def predict(state: str, game: str):
    # TEMP: Replace with your real engine
    if game == "P3":
        nums = ["123", "317", "456", "908", "789"]
    else:
        nums = ["1234", "3179", "5678", "8801", "9012"]

    return {
        "state": state,
        "game": game,
        "numbers": nums
    }

# ---------------------------
# RUNDOWN ENDPOINT
# ---------------------------
@app.get("/rundown")
def rundown(state: str):
    # TEMP: Replace with real rundown logic
    return {
        "state": state,
        "rundown": [
            ["1", "2", "3"],
            ["4", "5", "6"],
            ["7", "8", "9"]
        ]
    }

# ---------------------------
# ANALYZE ENDPOINT (CORNER ENGINE)
# ---------------------------
@app.post("/analyze")
def analyze(req: AnalyzeRequest):
    """
    Run the 3175 Corner-Pair Engine on a single draw.
    """
    try:
        alpha = req.alpha if req.alpha is not None else 0.8

        result = analyze_draw_with_grid(
            draw_id=req.draw_id,
            grid=req.rundown_grid,
            pick3_day=req.pick3_day,
            pick3_night=req.pick3_night,
            pick4=req.pick4,
            base_score=req.base_score,
            alpha=alpha
        )

        return {"ok": True, "result": result}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Corner analysis failed: {e}")


# ---------------------------
# DIRECTOR MODE — 3175 ENGINE
# ---------------------------
@app.post("/director/3175")
def director_3175(req: Director3175Request):
    """
    Run the full 3175 Director Mode engine.
    """
    try:
        history = req.history
        pred = run_3175_engine(history)
        alert = director_mode_3175_monitor(pred)

        return {
            "mode": "DIRECTOR",
            "strategy": "3175",
            "prediction": pred,
            "alert": alert
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"3175 Director Mode failed: {e}")
