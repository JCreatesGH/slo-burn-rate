"""Command-line SLO burn-rate calculator and Prometheus rule generator: `burnrate`."""
from __future__ import annotations
import argparse
import json
import math
import sys
from typing import Dict, List, Optional

from .budget import error_budget, burn_rate, budget_consumed, time_to_exhaustion
from .rules import SLO, burn_rate_rules, to_prometheus_yaml

DEFAULT_ERROR_QUERY = (
    'sum(rate(http_requests_total{code=~"5.."}[{window}]))'
    ' / sum(rate(http_requests_total[{window}]))'
)


def _parse_labels(pairs: Optional[List[str]]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for p in pairs or []:
        if "=" not in p:
            raise ValueError(f"--label must be KEY=VALUE, got {p!r}")
        k, v = p.split("=", 1)
        out[k.strip()] = v.strip()
    return out


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="burnrate", description="SLO error-budget / burn-rate calculator and rule generator.")
    parser.add_argument("--target", type=float, required=True, help="SLO target, e.g. 0.999")
    parser.add_argument("--error-rate", type=float, default=None,
                        help="observed error ratio (0..1); required unless --rules")
    parser.add_argument("--window-hours", type=float, default=None,
                        help="window to report budget consumed over")
    parser.add_argument("--slo-days", type=float, default=30, help="SLO period in days (default 30)")
    parser.add_argument("--json", action="store_true", help="emit JSON")
    # rule-generation mode
    parser.add_argument("--rules", action="store_true",
                        help="emit deployable Prometheus burn-rate alerting rules")
    parser.add_argument("--name", default="MySLO", help="SLO name used in alert names/labels")
    parser.add_argument("--error-query", default=DEFAULT_ERROR_QUERY,
                        help="error-ratio PromQL with a {window} placeholder")
    parser.add_argument("--for", dest="alert_for", default=None,
                        help="optional Prometheus `for:` duration on each alert")
    parser.add_argument("--label", action="append", metavar="KEY=VALUE",
                        help="extra label on every alert (repeatable)")
    args = parser.parse_args(argv)

    if args.rules:
        try:
            labels = _parse_labels(args.label)
            slo = SLO(name=args.name, target=args.target, error_query=args.error_query,
                      labels=labels, alert_for=args.alert_for)
            doc = burn_rate_rules(slo)
        except ValueError as e:
            print(f"error: {e}", file=sys.stderr)
            return 2
        print(json.dumps(doc, indent=2) if args.json else to_prometheus_yaml(doc).rstrip("\n"))
        return 0

    if args.error_rate is None:
        print("error: --error-rate is required (or pass --rules)", file=sys.stderr)
        return 2

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
