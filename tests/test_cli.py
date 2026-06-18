import json
import pytest
from burnrate.cli import main


def test_cli_over_budget_exits_1(capsys):
    code = main(["--target", "0.999", "--error-rate", "0.015"])
    out = capsys.readouterr().out
    assert code == 1
    assert "15.00x" in out and "OVER budget" in out


def test_cli_within_budget_exits_0(capsys):
    code = main(["--target", "0.999", "--error-rate", "0.0005"])
    assert code == 0
    assert "within budget" in capsys.readouterr().out


def test_cli_json_includes_budget_consumed(capsys):
    code = main(["--target", "0.999", "--error-rate", "0.0144",
                 "--window-hours", "1", "--json"])
    data = json.loads(capsys.readouterr().out)
    assert code == 1
    assert data["burn_rate"] == pytest.approx(14.4)
    assert data["budget_consumed"] == pytest.approx(0.02, rel=1e-6)


def test_cli_invalid_target(capsys):
    code = main(["--target", "1.0", "--error-rate", "0.01"])
    assert code == 2
    assert "error" in capsys.readouterr().err


def test_cli_requires_error_rate_without_rules(capsys):
    code = main(["--target", "0.999"])
    assert code == 2
    assert "--error-rate is required" in capsys.readouterr().err


def test_cli_rules_emits_yaml(capsys):
    code = main(["--target", "0.999", "--rules", "--name", "Checkout", "--label", "team=core"])
    out = capsys.readouterr().out
    assert code == 0
    assert out.startswith("groups:")
    assert "CheckoutErrorBudgetBurnPage" in out and "severity: " in out
    assert "team: " in out


def test_cli_rules_json(capsys):
    code = main(["--target", "0.999", "--rules", "--json"])
    data = json.loads(capsys.readouterr().out)
    assert code == 0
    assert data["groups"][0]["rules"]
