from unittest.mock import MagicMock

from app.services.prompt_builder import build_prompt


def _make_session(cfg=None):
    s = MagicMock()
    s.track_name = "Suzuka Circuit"
    s.manual_config = cfg
    return s


def _make_car(profile=None):
    c = MagicMock()
    c.name = "Porsche 911 GT3 (992)"
    c.category = "N700"
    c.tuning_profile = profile
    return c


def _make_lap(oversteer=5, bottom_out=0, tyre_fl=90.0):
    l = MagicMock()
    l.lap_time_ms = 128_000
    l.oversteer_events = oversteer
    l.understeer_events = 2
    l.wheel_lock_events = 1
    l.wheelspin_events = 0
    l.bottom_out_events = bottom_out
    l.tyre_temp_fl = tyre_fl
    l.tyre_temp_fr = 91.0
    l.tyre_temp_rl = 88.0
    l.tyre_temp_rr = 89.0
    return l


def test_prompt_contains_track():
    prompt = build_prompt(_make_session(), None, [_make_lap()])
    assert "Suzuka Circuit" in prompt


def test_prompt_no_aero_when_not_in_profile():
    profile = {
        "suspension": {"ranges": {"spring_rate_front": [3.0, 15.0]}}
    }
    prompt = build_prompt(_make_session(), _make_car(profile), [_make_lap()])
    assert "Aerodynamics" not in prompt
    assert "spring_rate_front" in prompt.lower() or "Spring Rate Front" in prompt


def test_prompt_includes_aero_when_in_profile():
    profile = {
        "aerodynamics": {"ranges": {"downforce_front": [0, 50], "downforce_rear": [0, 50]}}
    }
    prompt = build_prompt(_make_session(), _make_car(profile), [_make_lap()])
    assert "Aerodynamics" in prompt


def test_prompt_no_profile_warning():
    prompt = build_prompt(_make_session(), _make_car(profile=None), [_make_lap()])
    assert "No tuning profile" in prompt
