import math
import pytest
from burnrate import (
    error_budget, burn_rate, budget_consumed, time_to_exhaustion,
    burn_rate_threshold, remaining_budget, error_budget_minutes, error_budget_requests,
    Budget, WINDOWS,
)


def test_error_budget_minutes_matches_the_famous_numbers():
    assert error_budget_minutes(0.999) == pytest.approx(43.2)     # 99.9% / 30d
    assert error_budget_minutes(0.9999) == pytest.approx(4.32)    # 99.99%
    assert error_budget_minutes(0.999, slo_window_days=7) == pytest.approx(10.08)


def test_error_budget_requests():
    assert error_budget_requests(0.999, 1_000_000) == pytest.approx(1000)
    with pytest.raises(ValueError):
        error_budget_requests(0.999, -1)


def test_error_budget():
    assert error_budget(0.999) == pytest.approx(0.001)
    assert error_budget(0.99) == pytest.approx(0.01)
    with pytest.raises(ValueError):
        error_budget(1.0)


def test_burn_rate():
    # erroring at exactly the budget rate -> 1x
    assert burn_rate(0.001, 0.999) == pytest.approx(1.0)
    # 10x the budget
    assert burn_rate(0.01, 0.999) == pytest.approx(10.0)


def test_budget_consumed():
    # 1h at 14.4x burn on a 30d window ~ 2% of the budget
    c = budget_consumed(0.001 * 14.4, 0.999, window_hours=1, slo_window_days=30)
    assert c == pytest.approx(0.02, rel=1e-6)


def test_time_to_exhaustion():
    # at 1x burn, a 30d (720h) budget lasts the full window
    assert time_to_exhaustion(0.001, 0.999, 30) == pytest.approx(720)
    # at 2x burn it lasts half
    assert time_to_exhaustion(0.002, 0.999, 30) == pytest.approx(360)
    assert math.isinf(time_to_exhaustion(0.0, 0.999))


def test_budget_dataclass():
    b = Budget(target=0.995)
    assert b.budget == pytest.approx(0.005)
    assert b.burn_rate(0.05) == pytest.approx(10.0)


def test_burn_rate_threshold_inverts_budget_consumed():
    # 2% of the budget in 1h over a 30d window is the canonical 14.4x.
    assert burn_rate_threshold(0.02, 1, 30) == pytest.approx(14.4)
    with pytest.raises(ValueError):
        burn_rate_threshold(0.02, 0)


def test_window_thresholds_match_the_formula():
    # The standard WINDOWS table must be derivable from budget_pct over long_h.
    for w in WINDOWS:
        derived = burn_rate_threshold(w["budget_pct"] / 100.0, w["long_h"], 30)
        assert derived == pytest.approx(w["threshold"], rel=1e-6)


def test_remaining_budget():
    assert remaining_budget(0.25) == pytest.approx(0.75)
    assert remaining_budget(1.5) == 0.0   # clamped, never negative
