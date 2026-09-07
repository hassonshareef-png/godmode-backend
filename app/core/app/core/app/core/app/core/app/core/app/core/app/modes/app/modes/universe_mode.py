from app.modes.director_mode import analyze_draw


def analyze_universe(draws: list[dict]) -> list[dict]:
    """
    Universe Mode: analyze multiple draws across states.
    draws: [
      {"state": "PA", "draw": "5061", "date": 2, "month": 7},
      ...
    ]
    """
    results = []
    for d in draws:
        analysis = analyze_draw(d["draw"], d["date"], d["month"])
        analysis["state"] = d["state"]
        results.append(analysis)
    return results
