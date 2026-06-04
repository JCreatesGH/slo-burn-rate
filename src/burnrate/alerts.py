"""Multi-window, multi-burn-rate alerting (Google SRE Workbook model)."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional
from .budget import burn_rate


class AlertTier(str, Enum):
    PAGE = "page"
    TICKET = "ticket"
    NONE = "none"


# (long_window_hours, short_window_hours, burn_threshold, tier, budget_consumed_pct)
WINDOWS = [
    {"long_h": 1, "short_h": 5 / 60, "threshold": 14.4, "tier": AlertTier.PAGE, "budget_pct": 2.0},
    {"long_h": 6, "short_h": 30 / 60, "threshold": 6.0, "tier": AlertTier.PAGE, "budget_pct": 5.0},
    {"long_h": 24, "short_h": 2, "threshold": 3.0, "tier": AlertTier.TICKET, "budget_pct": 10.0},
    {"long_h": 72, "short_h": 6, "threshold": 1.0, "tier": AlertTier.TICKET, "budget_pct": 10.0},
]


@dataclass
class Decision:
    fired: bool
    tier: AlertTier
    reason: str
    long_burn: float
    short_burn: float


def multi_window_alert(error_rate_long: float, error_rate_short: float, target: float,
                       threshold: float) -> bool:
    """Fire only when BOTH the long and short windows exceed the burn threshold.
    The short window prevents alerting on an issue that has already recovered."""
    bl = burn_rate(error_rate_long, target)
    bs = burn_rate(error_rate_short, target)
    return bl >= threshold and bs >= threshold


def evaluate_policy(target: float, error_rates: Dict[float, float]) -> Decision:
    """error_rates maps window_hours -> observed error rate. Returns the most
    severe alert that fires across the standard window pairs."""
    best: Optional[Decision] = None
    for w in WINDOWS:
        long_h, short_h = w["long_h"], w["short_h"]
        if long_h not in error_rates or short_h not in error_rates:
            continue
        bl = burn_rate(error_rates[long_h], target)
        bs = burn_rate(error_rates[short_h], target)
        fired = bl >= w["threshold"] and bs >= w["threshold"]
        if fired:
            d = Decision(True, w["tier"],
                         f"{long_h}h & {short_h*60:.0f}m burn >= {w['threshold']}x", bl, bs)
            if best is None or _severity(d.tier) > _severity(best.tier):
                best = d
    return best or Decision(False, AlertTier.NONE, "within budget", 0.0, 0.0)


def _severity(tier: AlertTier) -> int:
    return {AlertTier.PAGE: 2, AlertTier.TICKET: 1, AlertTier.NONE: 0}[tier]
