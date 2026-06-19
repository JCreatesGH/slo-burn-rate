"""Generate deployable Prometheus multi-window burn-rate alerting rules.

The library computes the math; this turns an SLO definition into the rule group
you actually ship to Prometheus — one alert per tier, OR-ing every window pair
in that tier (the long *and* short window must both exceed the burn threshold).
The YAML emitter is hand-rolled so the package keeps zero runtime dependencies.
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .budget import error_budget
from .alerts import WINDOWS, AlertTier


def duration_str(hours: float) -> str:
    """Render an hour count as a Prometheus duration string: 1 -> '1h',
    5/60 -> '5m', 0.5 -> '30m', 72 -> '72h'."""
    minutes = round(hours * 60)
    if minutes <= 0:
        raise ValueError("window must be positive")
    if minutes % 60 == 0:
        return f"{minutes // 60}h"
    return f"{minutes}m"


@dataclass
class SLO:
    """An SLO to generate alerts for.

    error_query is an error-ratio PromQL expression containing a literal
    ``{window}`` placeholder, e.g.::

        sum(rate(http_requests_total{code=~"5.."}[{window}]))
          / sum(rate(http_requests_total[{window}]))
    """
    name: str
    target: float
    error_query: str
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)
    alert_for: Optional[str] = None     # optional Prometheus `for:` duration


_TIER_SUFFIX = {AlertTier.PAGE: "Page", AlertTier.TICKET: "Ticket"}


def _num(x: float) -> str:
    """Compact float that stays a valid PromQL literal (0.0144, not 0.014399…)."""
    return f"{x:.10g}"


def _metric_safe(name: str) -> str:
    """Coerce an SLO name into a valid Prometheus metric-name segment."""
    safe = re.sub(r"[^a-zA-Z0-9_]", "_", name)
    return safe or "slo"


def burn_rate_rules(slo: SLO, windows: Optional[List[dict]] = None,
                    record: bool = False) -> dict:
    """Build a Prometheus rule-group dict from an SLO. Threshold for each window
    is ``burn_threshold * error_budget`` so the expression compares directly
    against the observed error ratio.

    With ``record=True`` (the production pattern used by Sloth/Pyrra), each window's
    error ratio is precomputed into a ``<name>:sli_error:ratio_rate<window>`` recording
    rule and the alerts reference that metric — far cheaper to evaluate than inlining
    the full query into every alert, and easier to graph."""
    if "{window}" not in slo.error_query:
        raise ValueError("error_query must contain a '{window}' placeholder")
    budget = error_budget(slo.target)                  # validates target
    wins = windows if windows is not None else WINDOWS

    by_tier: Dict[AlertTier, List[dict]] = {}
    for w in wins:
        by_tier.setdefault(w["tier"], []).append(w)

    metric_base = _metric_safe(slo.name)

    def ratio_expr(hours: float) -> str:
        """The error-ratio expression for a window — a recorded metric, or inline."""
        d = duration_str(hours)
        if record:
            return f"{metric_base}:sli_error:ratio_rate{d}"
        return slo.error_query.replace("{window}", d)   # plain replace: PromQL has `{...}`

    rules: List[dict] = []

    # Recording rules come first so Prometheus has the metric before the alerts run.
    if record:
        seen: List[str] = []
        for w in wins:
            if w["tier"] == AlertTier.NONE:
                continue
            for h in (w["long_h"], w["short_h"]):
                d = duration_str(h)
                if d in seen:
                    continue
                seen.append(d)
                rules.append({
                    "record": f"{metric_base}:sli_error:ratio_rate{d}",
                    "expr": slo.error_query.replace("{window}", d),
                    "labels": {"slo": slo.name, **slo.labels},
                })

    for tier, ws in by_tier.items():
        if tier == AlertTier.NONE:
            continue
        conditions = []
        for w in ws:
            thr = _num(w["threshold"] * budget)
            lq, sq = ratio_expr(w["long_h"]), ratio_expr(w["short_h"])
            conditions.append(f"({lq} > {thr} and {sq} > {thr})")
        rule = {
            "alert": f"{slo.name}ErrorBudgetBurn{_TIER_SUFFIX[tier]}",
            "expr": "\nor\n".join(conditions),
            "labels": {"severity": tier.value, "slo": slo.name, **slo.labels},
            "annotations": {
                "summary": f"{slo.name} is burning its error budget too fast ({tier.value})",
                **slo.annotations,
            },
        }
        if slo.alert_for:
            rule["for"] = slo.alert_for
        rules.append(rule)

    return {"groups": [{"name": f"{slo.name}-slo-burn-rate", "rules": rules}]}


def _scalar(v) -> str:
    """Double-quote a value so PromQL/YAML special characters survive."""
    return '"' + str(v).replace("\\", "\\\\").replace('"', '\\"') + '"'


def to_prometheus_yaml(doc: dict) -> str:
    """Serialize a rule-group dict (from burn_rate_rules) to Prometheus rule
    YAML, with multi-line exprs as literal block scalars. No external deps."""
    lines: List[str] = ["groups:"]
    for g in doc["groups"]:
        lines.append(f"  - name: {_scalar(g['name'])}")
        lines.append("    rules:")
        for r in g["rules"]:
            if "record" in r:
                lines.append(f"      - record: {_scalar(r['record'])}")
            else:
                lines.append(f"      - alert: {_scalar(r['alert'])}")
            expr = r["expr"]
            if "\n" in expr:
                lines.append("        expr: |-")
                for el in expr.split("\n"):
                    lines.append(f"            {el}" if el else "")
            else:
                lines.append(f"        expr: {_scalar(expr)}")
            if r.get("for"):
                lines.append(f"        for: {_scalar(r['for'])}")
            for section in ("labels", "annotations"):
                data = r.get(section)
                if data:
                    lines.append(f"        {section}:")
                    for k, v in data.items():
                        lines.append(f"          {k}: {_scalar(v)}")
    return "\n".join(lines) + "\n"
