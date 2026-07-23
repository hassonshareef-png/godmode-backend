from dataclasses import dataclass

SHAPES = {
    "straight": 2,
    "l_shape": 2,
    "repeat": 2,
    "borrow": 1,
    "mirror": 1,
    "chaos": 0,
}

@dataclass
class StateProfile:
    name: str
    mirror_level: int
    date_use: int
    pattern_strength: int
    chaos_level: int
    repeat_level: int
    uses_3175_well: int
    shape_profile: dict

STATE_PROFILES = {
    "MO": StateProfile("Missouri", 2, 1, 2, 1, 2, 2,
                       {"straight": 2, "l_shape": 2, "repeat": 2, "borrow": 2, "mirror": 1}),
    "NM": StateProfile("New Mexico", 2, 2, 2, 2, 2, 2,
                       {"straight": 2, "l_shape": 2, "repeat": 2, "borrow": 1, "mirror": 2}),
    "OH": StateProfile("Ohio", 0, 0, 2, 0, 2, 2,
                       {"straight": 2, "l_shape": 1, "repeat": 2, "borrow": 1, "mirror": 0}),
    "GA": StateProfile("Georgia", 0, 1, 2, 0, 2, 2,
                       {"straight": 2, "l_shape": 1, "repeat": 2, "borrow": 1, "mirror": 0}),
    "FL": StateProfile("Florida", 0, 1, 2, 0, 2, 2,
                       {"straight": 2, "l_shape": 1, "repeat": 2, "borrow": 1, "mirror": 0}),
    "TX": StateProfile("Texas", 0, 1, 2, 0, 2, 2,
                       {"straight": 2, "l_shape": 1, "repeat": 2, "borrow": 1, "mirror": 0}),
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

def get_state_profile(code: str) -> StateProfile | None:
    return STATE_PROFILES.get(code.upper())

def godmode_weights(code: str) -> dict:
    profile = get_state_profile(code)
    if not profile:
        return {}
    return {
        "mirror_weight": profile.mirror_level,
        "date_weight": profile.date_use,
        "pattern_weight": profile.pattern_strength,
        "chaos_weight": profile.chaos_level,
        "repeat_weight": profile.repeat_level,
        "rundown_3175_weight": profile.uses_3175_well,
        "shape_profile": profile.shape_profile,
    }
