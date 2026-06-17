"""Core error-budget math (pure)."""
from __future__ import annotations
from dataclasses import dataclass


def error_budget(target: float) -> float:
    """Allowed failure ratio for an SLO target (0..1). 99.9% -> 0.001."""
    if not 0 < target < 1:
        raise ValueError("target must be between 0 and 1 (e.g. 0.999)")
    return 1.0 - target


def burn_rate(error_rate: float, target: float) -> float:
    """How fast the budget is being consumed vs. the sustainable rate.
    burn_rate = observed_error_rate / error_budget. 1.0 = exactly on budget."""
    budget = error_budget(target)
    return error_rate / budget if budget else float("inf")


def budget_consumed(error_rate: float, target: float, window_hours: float,
                    slo_window_days: float = 30) -> float:
    """Fraction of the *whole-period* error budget burned by `window_hours`
    spent at `error_rate`."""
    budget = error_budget(target)
    if budget == 0:
        return float("inf")
    total_hours = slo_window_days * 24
    return (error_rate * window_hours) / (budget * total_hours)


def time_to_exhaustion(error_rate: float, target: float, slo_window_days: float = 30) -> float:
    """Hours until the entire budget is gone at the current error rate
    (inf if under budget)."""
    br = burn_rate(error_rate, target)
    if br <= 0:
        return float("inf")
    total_hours = slo_window_days * 24
    return total_hours / br


def burn_rate_threshold(budget_fraction: float, alert_window_hours: float,
                        slo_window_days: float = 30) -> float:
    """Burn rate at which `budget_fraction` of the total budget is consumed within
    `alert_window_hours` — the inverse of `budget_consumed`, and the formula that
    derives the standard thresholds (e.g. 2% in 1h over 30d -> 14.4x)."""
    if alert_window_hours <= 0:
        raise ValueError("alert_window_hours must be positive")
    total_hours = slo_window_days * 24
    return budget_fraction * total_hours / alert_window_hours


def remaining_budget(consumed_fraction: float) -> float:
    """Fraction of the error budget still available, clamped to [0, 1]."""
    return max(0.0, 1.0 - consumed_fraction)


@dataclass
class Budget:
    target: float
    slo_window_days: float = 30

    @property
    def budget(self) -> float:
        return error_budget(self.target)

    def burn_rate(self, error_rate: float) -> float:
        return burn_rate(error_rate, self.target)

    def consumed(self, error_rate: float, window_hours: float) -> float:
        return budget_consumed(error_rate, self.target, window_hours, self.slo_window_days)
