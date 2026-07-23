from fastapi import FastAPI
from pydantic import BaseModel
from godmode.router import route_state

app = FastAPI(title="GODMODE API")

class PredictionRequest(BaseModel):
    state: str
    day: int

@app.post("/predict/pick4")
def predict_pick4(req: PredictionRequest):
    preds = route_state(req.state, req.day)
    return {"state": req.state.upper(), "day": req.day, "predictions": preds}
