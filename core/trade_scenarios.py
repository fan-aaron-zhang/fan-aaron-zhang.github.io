"""D0.4 trade-price scenario evidence, NOT fair-value or return forecasts.

A single ATR multiple is a normal-market shock proxy, not a hard stop or
worst-case loss. MA20/MA50 are observable reference levels, not predicted
resistance or intrinsic values. This module does not decide to trade.
"""
from __future__ import annotations
import math

SCENARIO_VERSION = "P0.1-reference-scenarios"

def finite_positive(value):
    try:
        value=float(value)
    except (ValueError, TypeError):
        return None
    return value if math.isfinite(value) and value>0 else None

def assess_price_scenario(*, price, atr_pct, ma20=None, ma50=None,
                          limit=None, quantity=0, fx_gbp_usd=None):
    p=finite_positive(price)
    a=finite_positive(atr_pct)
    entry=finite_positive(limit) if limit is not None else p
    fx=finite_positive(fx_gbp_usd)
    if p is None or a is None or entry is None or a>100:
        return {"Scenario status":"Unavailable", "Scenario version":SCENARIO_VERSION,
                "Scenario explanation":"Price/ATR data missing or invalid; no risk ratio calculated"}
    # Uses ATR expressed as a percentage of current close; scale to candidate
    # limit, rather than mistaking percent for dollar ATR.
    shock=round(entry * (1.5*a/100), 2)
    adverse=round(max(.01,entry-shock),2)
    refs=[float(v) for v in (finite_positive(ma20),finite_positive(ma50)) if v is not None and v>entry]
    recovery=round(min(refs),2) if refs else None
    upside=round(recovery-entry,2) if recovery is not None else None
    ratio=round(upside/shock,2) if upside is not None and shock>0 else None
    try:
        qty=int(quantity)
        if qty<0 or float(quantity)!=qty:qty=0
    except (TypeError, ValueError, OverflowError):
        qty=0
    stress_loss=round(qty*shock/fx,2) if qty>0 and fx is not None else None
    return {
        "Scenario status":"Reference only",
        "Scenario version":SCENARIO_VERSION,
        "Scenario entry USD":round(entry,2),
        "1.5 ATR adverse USD":adverse,
        "MA recovery reference USD":recovery,
        "Reward / shock reference":ratio,
        "Stress loss GBP":stress_loss,
        "Scenario explanation":("1.5 ATR is a volatility shock proxy, not a stop-loss or maximum loss; "
            "MA recovery level is not a profit target, and reward/shock ratio is NOT an expected-return estimate. "
            "No MA above entry means the upside reference remains N/A."),
    }
