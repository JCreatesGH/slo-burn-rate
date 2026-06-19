import pytest
from burnrate import SLO, burn_rate_rules, to_prometheus_yaml, duration_str, AlertTier

QUERY = ('sum(rate(http_requests_total{code=~"5.."}[{window}]))'
         ' / sum(rate(http_requests_total[{window}]))')


def test_duration_str():
    assert duration_str(1) == "1h"
    assert duration_str(5 / 60) == "5m"
    assert duration_str(0.5) == "30m"
    assert duration_str(2) == "2h"
    assert duration_str(72) == "72h"
    with pytest.raises(ValueError):
        duration_str(0)


def test_rules_have_one_alert_per_tier():
    doc = burn_rate_rules(SLO("Checkout", 0.999, QUERY))
    rules = doc["groups"][0]["rules"]
    alerts = {r["alert"]: r for r in rules}
    assert set(alerts) == {"CheckoutErrorBudgetBurnPage", "CheckoutErrorBudgetBurnTicket"}
    assert alerts["CheckoutErrorBudgetBurnPage"]["labels"]["severity"] == "page"
    assert alerts["CheckoutErrorBudgetBurnTicket"]["labels"]["severity"] == "ticket"
    assert alerts["CheckoutErrorBudgetBurnPage"]["labels"]["slo"] == "Checkout"


def test_page_expr_uses_correct_threshold_and_windows():
    doc = burn_rate_rules(SLO("Checkout", 0.999, QUERY))
    page = next(r for r in doc["groups"][0]["rules"] if r["alert"].endswith("Page"))
    expr = page["expr"]
    # 14.4 * (1 - 0.999) = 0.0144; 6 * 0.001 = 0.006
    assert "0.0144" in expr and "0.006" in expr
    # both window pairs present and OR-ed together
    assert "[1h]" in expr and "[5m]" in expr and "[6h]" in expr and "[30m]" in expr
    assert "\nor\n" in expr


def test_custom_labels_and_for():
    doc = burn_rate_rules(SLO("Api", 0.99, QUERY, labels={"team": "core"}, alert_for="2m"))
    page = next(r for r in doc["groups"][0]["rules"] if r["alert"].endswith("Page"))
    assert page["labels"]["team"] == "core"
    assert page["for"] == "2m"


def test_missing_window_placeholder_raises():
    with pytest.raises(ValueError):
        burn_rate_rules(SLO("X", 0.999, "sum(rate(errors[5m]))"))


def test_emitted_yaml_parses_and_matches():
    yaml = pytest.importorskip("yaml")
    doc = burn_rate_rules(SLO("Checkout", 0.999, QUERY, labels={"team": "core"}))
    text = to_prometheus_yaml(doc)
    parsed = yaml.safe_load(text)
    assert list(parsed.keys()) == ["groups"]
    group = parsed["groups"][0]
    assert group["name"] == "Checkout-slo-burn-rate"
    page = next(r for r in group["rules"] if r["alert"].endswith("Page"))
    # the multi-line expr survived the block scalar intact
    assert "http_requests_total" in page["expr"] and "\nor\n" in page["expr"]
    assert page["labels"]["severity"] == "page"
    assert page["labels"]["team"] == "core"
    assert page["annotations"]["summary"].startswith("Checkout is burning")


def test_recording_rules_precompute_each_window():
    doc = burn_rate_rules(SLO("Checkout", 0.999, QUERY), record=True)
    rules = doc["groups"][0]["rules"]
    recs = [r for r in rules if "record" in r]
    names = {r["record"] for r in recs}
    # one recording rule per distinct window, named like Sloth
    assert "Checkout:sli_error:ratio_rate1h" in names
    assert "Checkout:sli_error:ratio_rate5m" in names
    # the inlined query lives only in the recording rules now
    assert any("http_requests_total" in r["expr"] for r in recs)
    # alerts reference the recorded metric, not the raw query
    alerts = [r for r in rules if "alert" in r]
    page = next(r for r in alerts if r["alert"].endswith("Page"))
    assert "Checkout:sli_error:ratio_rate1h" in page["expr"]
    assert "http_requests_total" not in page["expr"]
    # recording rules come before the alerts (Prometheus evaluates in order)
    assert "record" in rules[0]


def test_recording_rule_yaml_is_valid_and_metric_name_sanitized():
    yaml = pytest.importorskip("yaml")
    doc = burn_rate_rules(SLO("my-checkout svc", 0.999, QUERY), record=True)
    parsed = yaml.safe_load(to_prometheus_yaml(doc))
    recs = [r for r in parsed["groups"][0]["rules"] if "record" in r]
    # name sanitized to a valid Prometheus metric segment
    assert recs and all(r["record"].startswith("my_checkout_svc:sli_error:ratio_rate") for r in recs)
