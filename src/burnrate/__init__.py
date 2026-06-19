"""burnrate: SLO error-budget and multi-window burn-rate alerting math."""
from .budget import (
    error_budget, budget_consumed, burn_rate, time_to_exhaustion,
    burn_rate_threshold, remaining_budget, error_budget_minutes, error_budget_requests, Budget,
)
from .alerts import WINDOWS, multi_window_alert, evaluate_policy, AlertTier, Decision
from .rules import SLO, burn_rate_rules, to_prometheus_yaml, duration_str
__all__ = ["error_budget", "budget_consumed", "burn_rate", "time_to_exhaustion",
           "burn_rate_threshold", "remaining_budget", "error_budget_minutes",
           "error_budget_requests", "Budget",
           "WINDOWS", "multi_window_alert", "evaluate_policy", "AlertTier", "Decision",
           "SLO", "burn_rate_rules", "to_prometheus_yaml", "duration_str"]
__version__ = "0.3.0"
