"""Opportunity evidence keeps price-level references and decisions separate."""
from datetime import date
from core.decision_engine import evaluate_candidate

D=date(2026,11,8)
T={"Status":"RESEARCH ONLY","Quote date":"2026-11-06","Technical / 100":75,
   "ATR14 %":5.0,"MA20":98.0,"MA50":96.0}
F={"Quality / 100":75,"Quality model":"F0.5","Coverage %":100,
   "Quarter age days":35,"Business model":"Non-bank","Quarter fallback":False,
   "Revenue growth %":20,"Operating margin %":15,
   "Valuation":{"Forward P/E":45,"EV / Revenue":14}}

def plan(**changes):
 d=dict(ticker="EX",technical=T,current_close=100,price_date="2026-11-06",
        fx_rate=1.3,fx_date="2026-11-06",cash_gbp=9000,
        holding_shares=0,holding_value_gbp=0,swing_value_gbp=30000,
        total_portfolio_gbp=150000,regime={"regime":"Supportive","as_of":"2026-11-06"},
        event={"status":"Later","checked_on":"2026-11-08"},financial=F,as_of=D)
 d.update(changes)
 return evaluate_candidate(**d)

def test_caution_restricts_buy_without_pretending_intrinsic_value():
 r=plan()
 assert r['Buy shares']==0
 assert r['Action']=='Wait — valuation'
 assert 'EV/revenue' in r['Valuation caution']
 assert r['Technical support reference USD'] < 100
 assert r['Recovery reference USD'] >= 100
 assert 'MA20' in r['Reassessment trigger']

def test_no_caution_does_not_imply_cheap_and_buy_is_cash_capped():
 fin={**F,'Revenue growth %':40,'Valuation':{'Forward P/E':28,'EV / Revenue':7}}
 r=plan(financial=fin)
 assert r['Action'] in {'Buy near last close','Buy on pullback'}
 assert r['Buy amount GBP'] <= 3000
 assert 'NOT proof of cheapness' in r['Valuation caution']

def test_high_volatility_reduces_position_size():
 fin={**F,'Revenue growth %':40,'Valuation':{'Forward P/E':28,'EV / Revenue':7}}
 low=plan(financial=fin,technical={**T,'ATR14 %':3})
 high=plan(financial=fin,technical={**T,'ATR14 %':12})
 assert low['Buy amount GBP'] >= high['Buy amount GBP']

def test_amba_hold_still_has_clear_reassessment():
 a=plan(ticker='AMBA',holding_shares=185,holding_value_gbp=8050,
        technical={**T,'Technical / 100':20,'MA20':63.17,'MA50':65.61,'ATR14 %':6.86},
        current_close=58.55)
 assert a['Action']=='Hold / watch'
 assert a['Sell shares']==0
 assert '63.17' in a['Reassessment trigger']
