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
# 🔥 NEW: ANALYZE ENDPOINT
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
