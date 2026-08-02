from godmode.state_behavior import godmode_weights


def test_godmode_weights_unknown_state_returns_error_payload():
    result = godmode_weights("zz")
    assert result["error"] == "No profile found for state 'ZZ'"
    assert "ZZ" not in result["supported_states"]
    assert "MO" in result["supported_states"]
