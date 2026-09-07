from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Dict, Any

from app.modes.director_mode import analyze_draw
from app.modes.universe_mode import analyze_universe

app = FastAPI(
    title="GODMODE Backend",
    version="2.0.0",
    description="Lottery engine backend powering Director Mode and Universe Mode."
)


class DirectorRequest(BaseModel):
    draw: str
    date: int
    month: int


class UniverseDraw(BaseModel):
    state: str
    draw: str
    date: int
    month: int


class UniverseRequest(BaseModel):
    draws: List[UniverseDraw]


@app.get("/")
def root():
    return {
        "status": "online",
        "engine": "GODMODE++",
        "modes": ["director", "universe"]
    }


@app.post("/director/analyze")
def director_mode(req: DirectorRequest) -> Dict[str, Any]:
    result = analyze_draw(req.draw, req.date, req.month)
    return {
        "mode": "director",
        "input": req.dict(),
        "analysis": result
    }


@app.post("/universe/analyze")
def universe_mode(req: UniverseRequest) -> Dict[str, Any]:
    draw_list = [d.dict() for d in req.draws]
    results = analyze_universe(draw_list)
    return {
        "mode": "universe",
        "count": len(results),
        "analysis": results
    }


@app.get("/health")
def health_check():
    return {"status": "ok"}
