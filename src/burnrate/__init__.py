"""burnrate: SLO error-budget and multi-window burn-rate alerting math."""
from .budget import error_budget, budget_consumed, burn_rate, time_to_exhaustion, Budget
from .alerts import WINDOWS, multi_window_alert, evaluate_policy, AlertTier, Decision
__all__ = ["error_budget", "budget_consumed", "burn_rate", "time_to_exhaustion", "Budget",
           "WINDOWS", "multi_window_alert", "evaluate_policy", "AlertTier", "Decision"]
__version__ = "0.1.0"
