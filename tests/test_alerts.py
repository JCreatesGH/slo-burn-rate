from burnrate import multi_window_alert, evaluate_policy, AlertTier, WINDOWS


def test_multi_window_requires_both():
    # long window hot, short window already recovered -> no alert
    assert not multi_window_alert(0.02, 0.0, 0.999, threshold=14.4)
    # both hot -> alert
    assert multi_window_alert(0.02, 0.02, 0.999, threshold=14.4)


def test_evaluate_policy_pages_on_fast_burn():
    # 1h and 5m windows both burning at ~15x -> PAGE
    er = 0.001 * 15
    d = evaluate_policy(0.999, {1: er, 5/60: er, 6: 0, 30/60: 0})
    assert d.fired and d.tier == AlertTier.PAGE
    assert "14.4x" in d.reason


def test_evaluate_policy_ticket_on_slow_burn():
    # 24h & 2h windows burning at ~3x, fast windows quiet -> TICKET
    er = 0.001 * 3.2
    d = evaluate_policy(0.999, {1: 0, 5/60: 0, 24: er, 2: er, 72: 0, 6: 0})
    assert d.fired and d.tier == AlertTier.TICKET


def test_evaluate_policy_quiet():
    d = evaluate_policy(0.999, {1: 0.0001, 5/60: 0.0001})
    assert not d.fired and d.tier == AlertTier.NONE


def test_page_outranks_ticket():
    er_fast = 0.001 * 15
    er_slow = 0.001 * 3.2
    d = evaluate_policy(0.999, {1: er_fast, 5/60: er_fast, 24: er_slow, 2: er_slow})
    assert d.tier == AlertTier.PAGE


def test_window_table_shape():
    assert len(WINDOWS) == 4
    assert WINDOWS[0]["threshold"] == 14.4


def test_evaluate_policy_accepts_custom_windows():
    custom = [{"long_h": 2, "short_h": 0.25, "threshold": 5.0, "tier": AlertTier.PAGE, "budget_pct": 1.0}]
    er = 0.001 * 6
    d = evaluate_policy(0.999, {2: er, 0.25: er}, windows=custom)
    assert d.fired and d.tier == AlertTier.PAGE
    # The standard windows are not consulted when a custom set is passed.
    assert evaluate_policy(0.999, {1: er, 5 / 60: er}, windows=custom).fired is False
