"""D0.2 decision safety, sizing, and AMBA regression tests."""
from datetime import date
from core.decision_engine import evaluate_candidate

TODAY = date(2026, 11, 8)
TECH = {"Status": "RESEARCH ONLY", "Quote date": "2026-11-06",
        "Technical / 100": 77, "ATR14 %": 4.0, "MA20": 98.0, "MA50": 95.0}
REGIME = {"regime": "Supportive", "as_of": "2026-11-06"}
EVENT = {"status": "Later", "checked_on": "2026-11-08"}
FINANCIAL = {"Quality / 100": 72, "Quality model": "F0.5", "Coverage %": 100,
             "Quarter age days": 40, "Quarter fallback": False,
             "Business model": "Non-bank", "Valuation": {"Forward P/E": 24}}


def plan(**kw):
    d = dict(ticker="DDOG", technical=TECH, current_close=100, price_date="2026-11-06",
             fx_rate=1.3, fx_date="2026-11-06", cash_gbp=9000,
             holding_shares=10, holding_value_gbp=770, swing_value_gbp=30000,
             total_portfolio_gbp=150000, regime=REGIME, event=EVENT,
             financial=FINANCIAL, as_of=TODAY)
    d.update(kw)
    return evaluate_candidate(**d)


def test_conditional_buy_uses_quality_and_cash_cap():
    r = plan()
    assert r["Action"] in {"Buy on pullback", "Buy near last close"}
    assert 0 < r["Buy shares"]
    assert r["Buy amount GBP"] <= 3000
    assert r["Buy limit USD"] <= 100
    assert r["Quality"] == 72


def test_missing_financial_or_valuation_never_makes_up_buy():
    assert plan(financial={})["Buy shares"] == 0
    assert plan(financial={**FINANCIAL, "Valuation": {}})["Buy shares"] == 0
    assert plan(financial={**FINANCIAL, "Quarter fallback": True})["Buy shares"] == 0
    assert plan(financial={**FINANCIAL, "Quarter age days": 140})["Buy shares"] == 0


def test_cash_and_concentration_capacity():
    assert plan(cash_gbp=0)["Buy shares"] == 0
    assert plan(holding_value_gbp=12000)["Buy shares"] == 0
    assert plan(swing_value_gbp=50000, total_portfolio_gbp=150000)["Buy shares"] == 0


def test_event_and_regime_avoid_new_buy():
    assert plan(regime={"regime": "Defensive", "as_of": "2026-11-06"})["Buy shares"] == 0
    assert plan(event={"status": "Within 7 days", "checked_on": "2026-11-08"})["Buy shares"] == 0
    assert plan(event={"status": "Later", "days_until": 16, "checked_on": "2026-11-08"})["Buy shares"] == 0
    assert plan(event={"status": "Unknown", "checked_on": "2026-11-08"})["Action"] == "Review data"


def test_data_fail_closed():
    assert plan(total_portfolio_gbp=None)["Status"] == "Blocked"
    assert plan(fx_date="2026-10-22")["Status"] == "Blocked"
    assert plan(ledger_ok=False)["Status"] == "Blocked"
    assert plan(technical={**TECH, "MA20": None})["Status"] == "Blocked"


def test_amba_weak_trend_not_mechanical_trim():
    """Actual AMBA V1.8a problem: score 20 + £8k holding should not force 25% sale."""
    t = {**TECH, "Technical / 100": 20, "ATR14 %": 6.86,
         "MA20": 63.172, "MA50": 65.61}
    r = plan(ticker="AMBA", technical=t, current_close=58.55,
             holding_shares=185, holding_value_gbp=8049.72)
    assert r["Action"] == "Hold / watch"
    assert r["Sell shares"] == 0
    assert r["Sell limit USD"] is None


def test_sell_sizing_tied_to_overweight_not_fixed_quarter():
    t = {**TECH, "Technical / 100": 20}
    r = plan(technical=t, holding_shares=150, holding_value_gbp=15000)
    assert r["Action"] == "Trim on rebound"
    assert 0 < r["Sell shares"] < 150
    r2 = plan(holding_shares=250, holding_value_gbp=19500)
    assert r2["Action"] == "Reduce now — risk"
    assert r2["Sell shares"] > 0


def test_bank_not_approved_as_autonomous_buy():
    f = {**FINANCIAL, "Business model": "Bank/lending hybrid"}
    r = plan(ticker="SOFI", financial=f)
    assert r["Buy shares"] == 0
    assert "credit" in r["Rationale"].lower()


def test_weak_trend_is_hold_even_if_financials_missing():
    r = plan(technical={**TECH, "Technical / 100": 15}, financial={}, holding_value_gbp=2000)
    assert r["Action"] == "Hold / watch"
    assert r["Sell shares"] == 0
