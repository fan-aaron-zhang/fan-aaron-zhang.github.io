"""Explainable, descriptive regime diagnostics using Yahoo daily history.

M0.1 does not predict a return or alter trade quantities. Missing/stale data
must not be interpreted as risk-on. Data is aligned to the latest COMMON day.
"""
from __future__ import annotations

from datetime import date, datetime
from math import sqrt
import pandas as pd

REGIME_MODEL = "M0.1-research"
SYMBOLS = ("SPY", "QQQ", "IWM", "SMH")


def _normalize_close(frame):
    if frame is None or "Close" not in frame.columns:
        return None
    close = pd.to_numeric(frame["Close"], errors="coerce").dropna()
    if close.empty:
        return None
    close = close[close > 0].copy()
    idx = pd.to_datetime(close.index)
    if getattr(idx, "tz", None) is not None:
        idx = idx.tz_localize(None)
    close.index = idx.normalize()
    return close[~close.index.duplicated(keep="last")].sort_index()


def evaluate_market_regime(histories: dict, as_of: date | None = None) -> dict:
    """Returns evidence and conservative descriptive state, never Buy/Sell."""
    today = as_of or date.today()
    series, errors = {}, []
    for symbol in SYMBOLS:
        close = _normalize_close(histories.get(symbol))
        if close is None or len(close) < 210:
            errors.append(f"{symbol}: fewer than 210 usable daily closes")
        else:
            series[symbol] = close
    if errors:
        return {"status": "Unavailable", "regime": "Unknown", "as_of": None,
                "model": REGIME_MODEL, "reason": "; ".join(errors), "components": []}

    common = pd.concat([series[s].rename(s) for s in SYMBOLS], axis=1, join="inner").dropna()
    # 200-day moving average needs 200 aligned sessions and a 20-day comparator.
    if len(common) < 220:
        return {"status": "Unavailable", "regime": "Unknown", "as_of": None,
                "model": REGIME_MODEL, "reason": f"Only {len(common)} aligned trading days", "components": []}
    last_day = common.index[-1].date()
    age = (today - last_day).days
    if age < 0 or age > 5:
        return {"status": "Stale", "regime": "Unknown", "as_of": str(last_day),
                "model": REGIME_MODEL, "reason": f"Market closing data age {age} days", "components": []}
    parts = []
    for s in SYMBOLS:
        c = common[s]
        last = float(c.iloc[-1]); ma50 = float(c.iloc[-50:].mean())
        ma200 = float(c.iloc[-200:].mean())
        return20 = float((last / float(c.iloc[-21]) - 1) * 100)
        parts.append({"ETF": s, "Close": round(last, 2), "MA50": round(ma50, 2),
                      "MA200": round(ma200, 2), "Above MA50": last > ma50,
                      "Above MA200": last > ma200, "20D return %": round(return20, 2)})
    spy = common['SPY']
    spy_last = float(spy.iloc[-1]); spy_ma50 = float(spy.iloc[-50:].mean())
    spy_ma200 = float(spy.iloc[-200:].mean())
    prior_ma50 = float(spy.iloc[-70:-20].mean())
    breadth = sum(row["Above MA50"] for row in parts)
    daily = spy.pct_change().dropna().tail(20)
    realized_vol = float(daily.std() * sqrt(252) * 100)
    dd60 = float((spy_last / float(spy.tail(60).max()) - 1) * 100)
    # Simple, documented 3-state risk context: not optimized or backtested.
    if spy_last > spy_ma200 and spy_last > spy_ma50 and spy_ma50 > prior_ma50 and breadth >= 3:
        regime = "Supportive"
        rationale = "SPY above rising MA50 and MA200; >=3/4 ETFs above MA50"
    elif spy_last < spy_ma200 and (spy_last < spy_ma50 or breadth <= 1):
        regime = "Defensive"
        rationale = "SPY below MA200 and either below MA50 or weak ETF breadth"
    else:
        regime = "Mixed"
        rationale = "Trend/breadth are not sufficiently aligned"
    if realized_vol >= 30:
        risk = "Elevated"
    elif realized_vol >= 20:
        risk = "Watch"
    else:
        risk = "Normal"
    return {"status": "Research only", "regime": regime, "as_of": str(last_day),
            "model": REGIME_MODEL, "reason": rationale,
            "risk_volatility": risk, "spy_20d_realized_vol_pct": round(realized_vol, 1),
            "spy_drawdown_60d_pct": round(dd60, 1), "breadth_above_ma50": breadth,
            "components": parts,
            "caveat": "Four ETF proxies are not full-market breadth; past trends cannot predict returns."}
