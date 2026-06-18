# Changelog

All notable changes are documented here, following
[Keep a Changelog](https://keepachangelog.com/) and [SemVer](https://semver.org/).

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
