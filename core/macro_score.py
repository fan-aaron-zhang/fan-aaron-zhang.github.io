"""M0.2 research-only market/macro *risk environment* score.

Inputs are liquid market proxies, not GDP predictions. Requires complete and
fresh data for ALL factors; never silently normalizes absent factors. A high
score is a more supportive risk environment, not a prediction of returns.
"""
from __future__ import annotations
from datetime import date
import math
import pandas as pd
from core.market_regime import evaluate_market_regime, _normalize_close

MACRO_MODEL = 'M0.2-price-proxy-experimental'
MACRO_SYMBOLS = ('SPY', 'QQQ', 'IWM', 'SMH', '^VIX', '^TNX', 'HYG', 'LQD')


def evaluate_macro_score(histories, *, as_of=None):
    today = as_of or date.today()
    base = evaluate_market_regime(histories, as_of=today)
    fail = {"score": None, "status": "Unknown", "model": MACRO_MODEL,
            "as_of": base.get('as_of'), "components": {},
            "reason": "Missing or stale macro proxies; score withheld", "market_regime": base.get('regime','Unknown')}
    if base.get('regime') == 'Unknown':
        fail['reason'] = base.get('reason','Regime unavailable')
        return fail
    raw = {}
    for ticker in ('^VIX','^TNX','HYG','LQD'):
        c = _normalize_close(histories.get(ticker))
        if c is None or len(c) < 25:
            return dict(fail, reason=f'{ticker}: fewer than 25 usable daily closes')
        age = (today - c.index[-1].date()).days
        if not 0 <= age <= 5:
            return dict(fail, reason=f'{ticker}: price age {age} days')
        raw[ticker] = c
    # Date-align the extra proxies to avoid comparing asynchronous closing days.
    aligned = pd.concat([c.rename(t) for t,c in raw.items()], axis=1, join='inner').dropna()
    if len(aligned) < 21:
        return dict(fail, reason='Macro proxy dates do not have 21 aligned trading sessions')
    latest = aligned.index[-1].date()
    if (today - latest).days > 5:
        return dict(fail, reason='Combined macro proxy data is stale')
    values = aligned.iloc[-1]
    vix = float(values['^VIX'])
    tnx = float(values['^TNX']) # Yahoo ^TNX is yield * 10
    ratio = aligned['HYG'] / aligned['LQD']
    credit_return = float((ratio.iloc[-1] / ratio.iloc[-21] - 1)*100)
    yield_20d_bps = float((tnx - float(aligned['^TNX'].iloc[-21])) * 10)
    if not all(math.isfinite(v) for v in (vix, tnx, credit_return, yield_20d_bps)) or vix <= 0 or tnx <= 0:
        return dict(fail, reason='Macro proxy price invalid')
    # Weight 40 trend, 25 fear, 20 rates, 15 credit; transparent coarse tiers.
    breadth = int(base['breadth_above_ma50'])
    spy200 = next(p['Above MA200'] for p in base['components'] if p['ETF']=='SPY')
    trend = 10 * breadth + (0 if spy200 else -8)
    trend = max(0, min(40, trend))
    vol = 25 if vix < 18 else 18 if vix < 25 else 9 if vix < 35 else 0
    # 20D yield jumps constrain growth stock risk even when absolute yield low.
    rates = 20 if yield_20d_bps < 0 else 14 if yield_20d_bps < 20 else 7 if yield_20d_bps < 50 else 0
    credit = 15 if credit_return >= 1 else 11 if credit_return >= 0 else 6 if credit_return > -2 else 0
    score = int(trend + vol + rates + credit)
    label = 'Supportive' if score >= 70 else 'Cautious' if score >= 40 else 'Defensive'
    return {'score':score,'status':label,'model':MACRO_MODEL,
            'as_of':str(min(latest, date.fromisoformat(base['as_of']))),
            'market_regime':base['regime'],
            'components':{'Market trend / 40':trend,'Volatility / 25':vol,
                          'Rates / 20':rates,'Credit / 15':credit},
            'observed':{'VIX':round(vix,2),'10Y yield proxy %':round(tnx/10,2),
                        '10Y yield change 20D bp':round(yield_20d_bps,1),
                        'HYG/LQD ratio change 20D %':round(credit_return,2)},
            'reason':'Heuristic market-price risk proxies, not predictive macro forecasting; no backtested weights.'}
