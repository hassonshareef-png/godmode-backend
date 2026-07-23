from godmode.state_behavior import godmode_weights
from godmode.shapes import apply_shapes, missouri_family_for_date_sum, new_mexico_family_for_date_sum
from godmode.rundowns.rundown_3175 import run_3175
from godmode.prediction.pick4 import generate_pick4

def get_date_sum(day: int) -> int:
    return sum(int(d) for d in str(day)) % 10

class SimpleEngine:
    def __init__(self):
        self.shape_weights = {}

    def set_shape_weight(self, shape: str, weight: int):
        self.shape_weights[shape] = weight

def director_mode(state_code: str, day: int) -> list[str]:
    weights = godmode_weights(state_code)
    if not weights:
        return []

    date_sum = get_date_sum(day)

    # choose family by state
    if state_code.upper() == "MO":
        family = missouri_family_for_date_sum(date_sum)
    elif state_code.upper() == "NM":
        family = new_mexico_family_for_date_sum(date_sum)
    else:
        family = [date_sum, (date_sum + 1) % 10]

    engine = SimpleEngine()
    apply_shapes(engine, weights["shape_profile"])

    rundown_digits = []
    if weights["rundown_3175_weight"] >= 1:
        rundown_digits = run_3175(date_sum)

    return generate_pick4(family, engine.shape_weights, rundown_digits)

if __name__ == "__main__":
    # Example: Missouri today (July 23 → day=23 → date-sum=5)
    preds = director_mode("MO", 23)
    for p in preds[:50]:
        print(p)
