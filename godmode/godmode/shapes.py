def apply_shapes(engine, shape_profile: dict):
    """
    Tell the engine which shapes to emphasize based on state profile.
    engine is your prediction engine object.
    """
    for shape, weight in shape_profile.items():
        engine.set_shape_weight(shape, weight)


def missouri_family_for_date_sum(date_sum: int) -> list[int]:
    """
    Missouri-style family for date-sum (simple version).
    For 5 → [5, 6], etc.
    """
    if date_sum == 5:
        return [5, 6]
    return [date_sum, (date_sum + 1) % 10]


def new_mexico_family_for_date_sum(date_sum: int) -> list[int]:
    """
    New Mexico-style family for date-sum (similar to Missouri).
    """
    if date_sum == 5:
        return [5, 6]
    return [date_sum, (date_sum + 1) % 10]
