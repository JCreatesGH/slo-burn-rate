"""Command-line SLO burn-rate calculator: `burnrate`."""
from __future__ import annotations
import argparse
import json
import math
import sys
from typing import List, Optional

from .budget import error_budget, burn_rate, budget_consumed, time_to_exhaustion


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="burnrate", description="SLO error-budget / burn-rate calculator.")
    parser.add_argument("--target", type=float, required=True, help="SLO target, e.g. 0.999")
    parser.add_argument("--error-rate", type=float, required=True, help="observed error ratio (0..1)")
    parser.add_argument("--window-hours", type=float, default=None,
                        help="window to report budget consumed over")
    parser.add_argument("--slo-days", type=float, default=30, help="SLO period in days (default 30)")
    parser.add_argument("--json", action="store_true", help="emit JSON")
    args = parser.parse_args(argv)

    try:
        budget = error_budget(args.target)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    br = burn_rate(args.error_rate, args.target)
    tte = time_to_exhaustion(args.error_rate, args.target, args.slo_days)
    consumed = (budget_consumed(args.error_rate, args.target, args.window_hours, args.slo_days)
                if args.window_hours else None)
    over = br >= 1.0

    if args.json:
        print(json.dumps({
            "target": args.target,
            "error_budget": budget,
            "error_rate": args.error_rate,
            "burn_rate": br,
            "time_to_exhaustion_hours": None if math.isinf(tte) else tte,
            "budget_consumed": consumed,
            "over_budget": over,
        }, indent=2))
    else:
        print(f"SLO target:         {args.target * 100:.3f}%")
        print(f"error budget:       {budget:.6f}")
        print(f"observed error:     {args.error_rate:.6f}")
        print(f"burn rate:          {br:.2f}x   ({'OVER budget' if over else 'within budget'})")
        print(f"time to exhaustion: {'∞' if math.isinf(tte) else f'{tte:.1f}h'}")
        if consumed is not None:
            print(f"budget consumed:    {consumed * 100:.2f}% (over {args.window_hours:g}h)")

    return 1 if over else 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
