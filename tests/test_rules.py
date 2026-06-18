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
