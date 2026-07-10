def generate_730_rundown(start_num: str) -> list:
    """Generates a complete 730 lottery math rundown matrix."""
    try:
        digits = [int(d) for d in str(start_num).strip() if d.isdigit()]
        if len(digits) != 3:
            return []
    except ValueError:
        return []
        
    addends = [7, 3, 0]
    matrix = [digits.copy()]
    
    while True:
        next_row = [
            (matrix[-1][0] + addends[0]) % 10,
            (matrix[-1][1] + addends[1]) % 10,
            (matrix[-1][2] + addends[2]) % 10
        ]
        if next_row == digits:
            break
        matrix.append(next_row)
        
    # Format list of lists into a list of strings (e.g., ["514", "244"])
    return ["".join(map(str, row)) for row in matrix]
