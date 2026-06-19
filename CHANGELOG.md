# Changelog

All notable changes are documented here, following
[Keep a Changelog](https://keepachangelog.com/) and [SemVer](https://semver.org/).

## [0.3.0]

### Added
- **Recording-rule generation** — `burn_rate_rules(slo, record=True)` (CLI `--record`) emits a
  `<name>:sli_error:ratio_rate<window>` recording rule per window and references it from the
  alerts, the production pattern used by Sloth/Pyrra. Recording rules are emitted first so the
  metric exists before alerts evaluate, and the SLO name is sanitized to a valid metric name.
  `to_prometheus_yaml` now serializes `record:` rules.
- **`error_budget_minutes(target, slo_window_days=30)`** — allowed downtime in minutes
  (99.9% → 43.2 min/30d), and **`error_budget_requests(target, total)`** for request-based SLOs.
  The CLI report now shows `allowed downtime` and `--json` includes `error_budget_minutes`.

## [0.2.0]

### Added
- Deployable **Prometheus alerting-rule generation**: `SLO`, `burn_rate_rules()`
  (one alert per tier, OR-ing each window pair with the threshold pre-multiplied
  by the error budget), `to_prometheus_yaml()` (hand-rolled, zero runtime deps),
  and `duration_str()`.
- `burnrate --rules` CLI mode to emit the rule YAML (or `--json`).

## [0.1.0]

### Added
- Error-budget math: `error_budget`, `burn_rate`, `budget_consumed`,
  `time_to_exhaustion`, `burn_rate_threshold`, `remaining_budget`, `Budget`.
- Multi-window, multi-burn-rate alerting (`multi_window_alert`,
  `evaluate_policy`) following the Google SRE Workbook, and a `burnrate` CLI.
