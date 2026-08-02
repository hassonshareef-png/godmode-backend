# ============================================================
# GODMODE++ Numerology API Route
# ============================================================

from fastapi import APIRouter
from pydantic import BaseModel
from datetime import datetime

from app.core.numerology_engine import compute_numerology_features

router = APIRouter()

# ------------------------------------------------------------
# Request Model
# ------------------------------------------------------------

class NumerologyRequest(BaseModel):
    draw_number: str      # Example: "1234"
    draw_date: str        # ISO date: "2026-07-07"

# ------------------------------------------------------------
# Route: POST /numerology/score
# ------------------------------------------------------------

@router.post("/score")
def numerology_score(payload: NumerologyRequest):
    """
    Compute numerology features + BiasScore for a single draw.
    """

    # Convert date string → datetime
    draw_date = datetime.fromisoformat(payload.draw_date)

    # Compute numerology features
    features = compute_numerology_features(
        draw_number=payload.draw_number,
        draw_date=draw_date
    )

    return {
        "draw_number": payload.draw_number,
        "draw_date": payload.draw_date,
        **features
    }
