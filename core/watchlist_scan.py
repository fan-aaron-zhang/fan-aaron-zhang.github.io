"""Fast, technical-only 22-name screening; not position-aware trade decisions.

A screen cannot generate a Buy order or make financial/earnings claims. It
identifies names for full Decision Engine review; no workbook/market data
leaves the Streamlit session cache.
"""
from datetime import date
from config import WATCHLIST, SECTOR_BENCHMARKS, MARKET_BENCHMARK

SCAN_VERSION = "S0.1-technical-triage"


def triage(technical, *, held=False):
    """Transparent, intentionally conservative triage from T1.0 fields."""
    score = technical.get("Technical / 100")
    status = technical.get("Status", "UNAVAILABLE")
    if score is None or status != "RESEARCH ONLY":
        return "Data unavailable", status or "Technical/benchmark data incomplete", "Refresh/check source; no trading interpretation"
    close = technical.get("Close USD")
    ma20 = technical.get("MA20")
    ma50 = technical.get("MA50")
    ret20 = technical.get("Return 20D %")
    if any(x is None for x in (close, ma20, ma50, ret20)):
        return "Data unavailable", "Missing indicators", "Recheck source"
    if held and score < 30 and ret20 < -10:
        return "Risk review", "Held position; weak T1.0 trend and >10% 20D drawdown", "Review financial thesis, events and position sizing"
    if score >= 70 and close > ma20 and close > ma50:
        return "Research candidate", "Strong technical score with close above MA20 and MA50", "Check valuation, events, portfolio limits before any buy"
    if score >= 50:
        return "Watch", "Improving/mixed technical strength; not a verified entry", "Check momentum, valuation and earnings in Trade Decisions"
    reasons = []
    if close < ma20: reasons.append("below MA20")
    if close < ma50: reasons.append("below MA50")
    if ret20 < 0: reasons.append("20D momentum negative")
    if not reasons: reasons.append("composite technical strength below threshold")
    return "Wait", ", ".join(reasons), "Recheck on MA20 recovery, improved score, or new fundamentals"


def screen_from_technicals(technicals, holdings=()):
    """Pure transformation, safe to test with zero network calls."""
    held = set(holdings)
    output=[]
    for ticker in WATCHLIST:
        tech = technicals.get(ticker) or {}
        label, reason, trigger = triage(tech, held=ticker in held)
        output.append({"Ticker":ticker, "Screen":label, "Held":ticker in held,
                       "Technical":tech.get("Technical / 100"),
                       "Close USD":tech.get("Close USD"),
                       "MA20":tech.get("MA20"), "MA50":tech.get("MA50"),
                       "Return 20D %":tech.get("Return 20D %"),
                       "Price date":tech.get("Quote date"),
                       "Reason":reason, "Review trigger":trigger})
    priority={"Risk review":0,"Research candidate":1,"Watch":2,"Data unavailable":3,"Wait":4}
    output.sort(key=lambda r:(priority.get(r["Screen"],5), -(r["Technical"] or 0), r["Ticker"]))
    return output


def scan_watchlist(*, holdings=()):
    """One scan on request: share cached ETF bars and reuse cached histories."""
    from core.market_data import load_signal_history
    from core.scoring import compute_technical
    symbols = set(SECTOR_BENCHMARKS.values()) | {MARKET_BENCHMARK}
    benchmarks = {sym: load_signal_history(sym)[0] for sym in sorted(symbols)}
    technicals={}
    for ticker in WATCHLIST:
        history, _ = load_signal_history(ticker)
        sector = SECTOR_BENCHMARKS[ticker]
        technicals[ticker] = compute_technical(ticker, history,
                 benchmarks[MARKET_BENCHMARK], benchmarks[sector], sector)
    return {"version":SCAN_VERSION, "generated":str(date.today()),
            "rows":screen_from_technicals(technicals, holdings),
            "scope":"Technical T1.0 fast screen; NOT full financial/earnings/portfolio advice"}
