from datetime import date
from core.trade_scenarios import assess_price_scenario
from core.decision_engine import evaluate_candidate

def test_price_scenario_with_ma_and_fx():
    r=assess_price_scenario(price=100, atr_pct=4, ma20=110, ma50=120, limit=100, quantity=10, fx_gbp_usd=1.25)
    assert r['1.5 ATR adverse USD']==94
    assert r['MA recovery reference USD']==110
    assert r['Reward / shock reference']==round(10/6,2)
    assert r['Stress loss GBP']==48

def test_no_upside_reference_is_unknown_not_zero():
    r=assess_price_scenario(price=100, atr_pct=5, ma20=90, ma50=95)
    assert r['Reward / shock reference'] is None
    assert r['MA recovery reference USD'] is None

def test_missing_inputs_cannot_invent_scenario():
    assert assess_price_scenario(price=None,atr_pct=5)['Scenario status']=='Unavailable'
    assert assess_price_scenario(price=100,atr_pct=None)['Scenario status']=='Unavailable'

def test_weak_trend_not_trim_due_to_scenario():
    tech={'Status':'RESEARCH ONLY','Quote date':'2026-11-06','Technical / 100':20,
          'ATR14 %':6.86,'MA20':63.17,'MA50':65.61}
    r=evaluate_candidate('AMBA',tech,current_close=58.55,price_date='2026-11-06',
        fx_rate=1.34,fx_date='2026-11-06',cash_gbp=9000,holding_shares=185,
        holding_value_gbp=8050,swing_value_gbp=30000,total_portfolio_gbp=150000,
        regime={'regime':'Mixed','as_of':'2026-11-06'},
        event={'status':'Later','checked_on':'2026-11-08'},as_of=date(2026,11,8))
    assert r['Action']=='Hold / watch'
    assert r['Sell shares']==0
    assert r['Scenario entry USD']==58.55

def test_buy_risk_budget_and_stress():
    tech={'Status':'RESEARCH ONLY','Quote date':'2026-11-06','Technical / 100':77,
          'ATR14 %':10,'MA20':98,'MA50':95}
    fin={'Quality / 100':72,'Quality model':'F0.5','Coverage %':100,
         'Quarter age days':40,'Quarter fallback':False,'Business model':'Non-bank',
         'Valuation':{'Forward P/E':24}}
    r=evaluate_candidate('DDOG',tech,current_close=100,price_date='2026-11-06',
        fx_rate=1.3,fx_date='2026-11-06',cash_gbp=9000,holding_shares=0,
        holding_value_gbp=0,swing_value_gbp=30000,total_portfolio_gbp=150000,
        regime={'regime':'Supportive','as_of':'2026-11-06'},
        event={'status':'Later','checked_on':'2026-11-08'},financial=fin,
        as_of=date(2026,11,8))
    assert r['Buy shares']>0
    assert r['Stress loss GBP']<=150.01
    assert r['Sell shares']==0
