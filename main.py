from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import random

app = FastAPI()

# ===============================
# CORS (Fixes Network Error)
# ===============================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===============================
# MODELS
# ===============================

class LoginRequest(BaseModel):
    username: str
    password: str

class PredictRequest(BaseModel):
    god: bool = False
    universe: bool = False

class PickRequest(BaseModel):
    number: str

class DirectorRequest(BaseModel):
    seed: Optional[str] = None


# ===============================
# LOGIN (Matches Frontend)
# ===============================
@app.post("/login")
def login(req: LoginRequest):
    if req.username == "admin" and req.password == "8118":
        return {"god": True, "universe": True}
    return {"error": "Invalid username or password"}


# ===============================
# PREDICT (Matches Frontend)
# ===============================
@app.post("/predict")
def predict(req: PredictRequest):
    # Simple prediction engine
    nums = sorted(random.sample(range(0, 10), 3))
    return {"prediction": "".join(str(n) for n in nums)}


# ===============================
# DIRECTOR (Matches Frontend)
# ===============================
@app.post("/director")
def director(req: DirectorRequest):
    drift = random.choice([-2, -1, 0, 1, 2])
    base = [7, 14, 22, 31, 36]
    base = [max(1, min(39, n + drift)) for n in base]

    if req.seed:
        try:
            seed_num = int(req.seed)
        except:
            seed_num = 0
        base = [max(1, min(39, n + (seed_num % 10))) for n in base]

    base = sorted(set(base))

    return {
        "output": f"Compiled Prediction → {base} | Drift {drift} | Seed {req.seed or 'none'}",
        "numbers": base
    }


# ===============================
# PICK 3 (Matches Frontend)
# ===============================
@app.post("/pick3")
def pick3(req: PickRequest):
    if len(req.number) != 3 or not req.number.isdigit():
        return {"error": "Pick3 requires exactly 3 digits."}

    digits = [int(d) for d in req.number]
    s = sum(digits)

    return {
        "result": f"Pick 3 Engine → digits={digits}, sum={s}, root={s % 10}"
    }


# ===============================
# PICK 4 (Matches Frontend)
# ===============================
@app.post("/pick4")
def pick4(req: PickRequest):
    if len(req.number) != 4 or not req.number.isdigit():
        return {"error": "Pick4 requires exactly 4 digits."}

    digits = [int(d) for d in req.number]
    s = sum(digits)

    return {
        "result": f"Pick 4 Engine → digits={digits}, sum={s}, root={s % 10}"
    }

