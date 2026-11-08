"""Unchanged technical model T1.0; pure indicator and scoring functions."""
import math
import pandas as pd
from config import MODEL_VERSION


def rsi_wilder(close, period=14):
    delta = close.diff()
    ups = delta.clip(lower=0)
    downs = -delta.clip(upper=0)
    avg_up = ups.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_down = downs.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_up / avg_down.replace(0, float("nan"))
    result = 100 - 100 / (1 + rs)
    result = result.where(avg_down != 0, 100.0)
    result = result.where(~((avg_down == 0) & (avg_up == 0)), 50.0)
    return result

def compute_technical(symbol, data, market, sector, sector_ticker=None):
    """Experimental 100-point score; two benchmark returns on COMMON dates.

    This is not a trading signal. For any missing/stale benchmark, do not score.
    """
    output = {
        "Ticker": symbol, "Sector ETF": sector_ticker,
        "Quote date": None, "Close USD": None,
        "Trend / 30": None, "Momentum / 25": None,
        "RS Market / 8": None, "RS Sector / 12": None,
        "RSI / 15": None, "Volume / 10": None,
        "Technical / 100": None,
        "MA20": None, "MA50": None, "RSI14": None,
        "Return 5D %": None, "Return 20D %": None,
        "RS 20D vs SPY pp": None, "RS 20D vs Sector pp": None,
        "ATR14 %": None, "Status": "UNAVAILABLE",
    }
    if sector_ticker is None:
        output["Status"] = "No sector ETF configured"
        return output
    if any(x is None or x.empty for x in (data, market, sector)):
        output["Status"] = "Stock/benchmark price history unavailable"
        return output
    # Ensure latest close is common to all three, not a stale sector benchmark.
    common = data.index.intersection(market.index).intersection(sector.index)
    if len(common) < 100:
        output["Status"] = "Too few shared trading dates"
        return output
    d, m, b = (x.loc[common].copy() for x in (data, market, sector))
    last_day = common[-1]
    output["Quote date"] = str(last_day.date())
    current_day = pd.Timestamp.now(tz="UTC").tz_localize(None).normalize()
    latest_days = [x.index[-1] for x in (data, market, sector)]
    if (current_day - last_day).days > 5 or any((latest - last_day).days > 2 for latest in latest_days):
        output["Status"] = "STALE or mismatched quote dates: no score"
        return output
    close = d.Close
    ma20, ma50 = close.rolling(20).mean(), close.rolling(50).mean()
    rsi = rsi_wilder(close)
    prev_close = close.shift(1)
    tr = pd.concat([d.High - d.Low, (d.High - prev_close).abs(),
                    (d.Low - prev_close).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    ret5 = close.iloc[-1] / close.iloc[-6] - 1
    ret20 = close.iloc[-1] / close.iloc[-21] - 1
    m_ret20 = m.Close.iloc[-1] / m.Close.iloc[-21] - 1
    b_ret20 = b.Close.iloc[-1] / b.Close.iloc[-21] - 1
    rs_market = (ret20 - m_ret20) * 100
    rs_sector = (ret20 - b_ret20) * 100
    vol20 = d.Volume.iloc[-21:-1].mean()
    vr = d.Volume.iloc[-1] / vol20 if vol20 > 0 else float("nan")
    rsi_val = float(rsi.iloc[-1])
    check = [ret5, ret20, rs_market, rs_sector, vr, rsi_val,
             atr.iloc[-1], ma20.iloc[-1], ma50.iloc[-1], ma50.iloc[-21]]
    if not all(math.isfinite(float(v)) for v in check):
        output["Status"] = "Missing indicator inputs"
        return output
    trend = ((10 if close.iloc[-1] > ma20.iloc[-1] else 0)
             + (10 if ma20.iloc[-1] > ma50.iloc[-1] else 0)
             + (10 if ma50.iloc[-1] > ma50.iloc[-21] else 0))
    momentum = ((10 if ret5 > 0 else 0) + (10 if ret20 > 0 else 0)
                + (5 if ret20 > 0.05 else 0))
    rs_market_score = (4 if rs_market > 0 else 0) + (4 if rs_market > 5 else 0)
    rs_sector_score = (6 if rs_sector > 0 else 0) + (6 if rs_sector > 5 else 0)
    rsi_score = (15 if 40 <= rsi_val <= 70 else
                 (8 if 30 <= rsi_val < 40 else (5 if 70 < rsi_val <= 80 else 2)))
    vol_score = 10 if vr >= 1.2 and ret5 > 0 else (5 if vr >= 0.8 else 0)
    output.update({
        "Close USD": round(float(close.iloc[-1]), 3),
        "Trend / 30": trend, "Momentum / 25": momentum,
        "RS Market / 8": rs_market_score, "RS Sector / 12": rs_sector_score,
        "RSI / 15": rsi_score, "Volume / 10": vol_score,
        "Technical / 100": trend + momentum + rs_market_score + rs_sector_score + rsi_score + vol_score,
        "MA20": round(float(ma20.iloc[-1]), 3), "MA50": round(float(ma50.iloc[-1]), 3),
        "RSI14": round(rsi_val, 1),
        "Return 5D %": round(float(ret5 * 100), 2),
        "Return 20D %": round(float(ret20 * 100), 2),
        "RS 20D vs SPY pp": round(float(rs_market), 2),
        "RS 20D vs Sector pp": round(float(rs_sector), 2),
        "ATR14 %": round(float(atr.iloc[-1] / close.iloc[-1] * 100), 2),
        "Status": "RESEARCH ONLY",
    })
    return output

