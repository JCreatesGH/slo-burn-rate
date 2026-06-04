import math
import pytest
from burnrate import error_budget, burn_rate, budget_consumed, time_to_exhaustion, Budget


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
