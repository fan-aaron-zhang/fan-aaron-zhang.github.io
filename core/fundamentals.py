"""Yahoo snapshot normalization and experimental non-bank quality research.

Pure functions, no network, no Streamlit or portfolio/trading dependencies.
Yahoo financials do NOT reconstruct historic point-in-time fundamentals.
"""
from __future__ import annotations
from datetime import date
import math
import pandas as pd

QUALITY_MODEL_VERSION = "F0.5-quarter-fallback-experimental"
BANK_MODEL_VERSION = "B0.2-experimental"
FRESHNESS_WARN_DAYS = 120
FRESHNESS_HARD_STOP_DAYS = 210
BANK_WEIGHTS = {"Revenue growth": 25, "ROE": 30, "ROA": 20, "Equity/assets": 25}
BANK_SCALES = {
    "Revenue growth": [(-0.15, 0), (0, 7), (0.10, 15), (0.20, 20), (0.35, 25)],
    "ROE": [(-0.10, 0), (0, 7), (0.10, 17), (0.20, 25), (0.30, 30)],
    "ROA": [(-0.02, 0), (0, 5), (0.01, 12), (0.02, 17), (0.03, 20)],
    "Equity/assets": [(0.02, 0), (0.05, 8), (0.08, 16), (0.12, 22), (0.18, 25)],
}
BANK_TICKERS = frozenset({"NU", "SOFI"})  # Both are banking/lending businesses; separate from industrial scoring
SPECIAL_FINANCIAL_TICKERS = frozenset({"SOFI"})  # Distinguish hybrid bank from NU in report labels

# Yahoo row labels can change; candidates are preferred matches, not accounting guarantees.
FIELDS = {
    "revenue": ("Total Revenue", "Operating Revenue", "Total Revenues", "Revenues", "Revenue"),
    "operating_income": ("Operating Income", "Operating Income As Reported", "Operating Profit", "EBIT"),
    "net_income": ("Net Income", "Net Income Common Stockholders", "Net Income From Continuing Operation Net Minority Interest", "Net Income Including Noncontrolling Interests", "Net Income From Continuing Operations"),
    "operating_cashflow": ("Operating Cash Flow", "Cash Flow From Continuing Operating Activities",
                           "Cash Flow From Continuing Operating Activities Net", "Net Cash Provided By Operating Activities"),
    "capex": ("Capital Expenditure", "Capital Expenditures", "Purchase Of PPE", "Purchase Of Property Plant And Equipment"),
}
WEIGHTS = {"Revenue growth": 35, "Operating margin": 25, "Net margin": 20, "FCF margin": 20}
SCALES = {
    "Revenue growth": [(-0.10, 0), (0, 10), (0.10, 20), (0.20, 28), (0.30, 35)],
    "Operating margin": [(-0.20, 0), (0, 8), (0.10, 15), (0.20, 22), (0.30, 25)],
    "Net margin": [(-0.20, 0), (0, 8), (0.10, 14), (0.20, 20)],
    "FCF margin": [(-0.20, 0), (0, 8), (0.10, 14), (0.20, 20)],
}


def _frame(df):
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return pd.DataFrame()
    out = df.copy()
    try:
        out.columns = pd.to_datetime(out.columns, errors="coerce")
        out = out.loc[:, out.columns.notna()]
        return out.loc[:, ~out.columns.duplicated()].sort_index(axis=1, ascending=False)
    except Exception:
        return pd.DataFrame()


def _canonical(label):
    """Normalize whitespace/case/punctuation only, never fuzzy-match accounting concepts."""
    import re
    return re.sub(r"[^a-z0-9]", "", str(label).casefold())


def _matched_field(df, names):
    """Prefer exact Yahoo rows, then cautiously permit spelling/punctuation variants."""
    if df.empty:
        return None
    for name in names:
        if name in df.index:
            return name
    by_name = {_canonical(row): row for row in df.index}
    for name in names:
        if _canonical(name) in by_name:
            return by_name[_canonical(name)]
    return None


def _values(df, names):
    found = _matched_field(df, names)
    if found is None:
        return None
    row = pd.to_numeric(df.loc[found], errors="coerce")
    if isinstance(row, pd.DataFrame):
        row = row.iloc[0]
    return row


def _period_value(df, names, quarter_end):
    """Read only a value matching the income-statement quarter; don't mix periods."""
    if quarter_end is None:
        return None
    series = _values(df, names)
    if series is None:
        return None
    for period, value in series.items():
        if period.date() == quarter_end:
            try:
                number = float(value)
                return number if math.isfinite(number) else None
            except (TypeError, ValueError):
                return None
    return None


def _choose_income_quarter(inc, cf):
    """Choose the most recent usable *single* quarterly period.

    Prefer the newest period with revenue, operating income and net income.
    If a newer period is partially populated, fall back to a complete period
    (at most two preceding reported quarterly columns). Do not choose an old
    quarter just to recover FCF when current income statements are complete.
    Cash-flow availability is scored separately and never copied across dates.
    """
    if inc.empty:
        return None, None, "No quarterly income statement"
    latest = max(inc.columns).date()
    periods = [p.date() for p in inc.columns]
    if len(periods) > 1:
        # Exclude accidental FY columns for quarterly sources; a gap in the
        # statement does not justify unlimited backward fallback.
        candidates = periods[:3]
    else:
        candidates = periods
    required = ("revenue", "operating_income", "net_income")
    for quarter in candidates:
        if all(_period_value(inc, FIELDS[k], quarter) is not None for k in required):
            reason = ("Latest income quarter usable" if quarter == latest else
                      "Fallback: latest income quarter has missing core values")
            return quarter, latest, reason
    # Do not make a complete quarter up when no income period is complete.
    return latest, latest, "No fully populated income quarter in recent periods"


def _growth_for_quarter(inc, annual, quarter_end):
    """Comparable quarter YoY if available; otherwise explicit lagged FY YoY.

    Never compare different fiscal quarters (e.g. September to June).
    """
    current = _period_value(inc, FIELDS["revenue"], quarter_end)
    if current is not None and quarter_end is not None:
        prior = quarter_end.replace(year=quarter_end.year - 1) if not (
            quarter_end.month == 2 and quarter_end.day == 29) else date(quarter_end.year-1,2,28)
        comparable = _period_value(inc, FIELDS["revenue"], prior)
        if comparable is not None and comparable > 0:
            return current / comparable - 1, "Quarter YoY (selected quarter)"
    yr = _values(annual, FIELDS["revenue"])
    if yr is not None:
        valid = [(dt.date(), float(v)) for dt, v in yr.items() if pd.notna(v)]
        # Annual records ending after selected quarter are inappropriate for
        # fallback as they would be chronologically inconsistent.
        valid = [(dt, value) for dt, value in valid if quarter_end is None or dt <= quarter_end]
        if len(valid) >= 2 and valid[1][1] > 0:
            return valid[0][1] / valid[1][1] - 1, "Fiscal year YoY (lagged)"
    return None, "Unavailable"


def _source_audit(inc, cf, annual, quarter_end):
    """Distinguish absent mapping, empty source, missing value and unmatched quarter."""
    checks = [
        ("Quarterly revenue", inc, FIELDS["revenue"], True),
        ("Annual revenue", annual, FIELDS["revenue"], False),
        ("Operating income", inc, FIELDS["operating_income"], True),
        ("Net income", inc, FIELDS["net_income"], True),
        ("Operating cash flow", cf, FIELDS["operating_cashflow"], True),
        ("Capital expenditure", cf, FIELDS["capex"], True),
    ]
    out = []
    for label, frame, names, align in checks:
        matched = _matched_field(frame, names)
        val = (_period_value(frame, names, quarter_end) if align
               else _latest(_values(frame, names)))
        latest_date = max(frame.columns).date() if not frame.empty else None
        period_exists = bool(quarter_end and not frame.empty and
                             any(c.date() == quarter_end for c in frame.columns))
        if frame.empty:
            reason = "Statement empty or unavailable"
        elif matched is None:
            reason = "Yahoo row absent or unmapped"
        elif align and not period_exists:
            reason = "Quarter missing from this statement"
        elif val is None:
            reason = "Field exists but selected-period value missing/non-numeric"
        else:
            reason = "Matched and usable"
        out.append({"Field": label, "Yahoo row": matched or "Not mapped",
                    "Latest value": val, "Latest period": str(latest_date) if latest_date else None,
                    "Aligned quarter": str(quarter_end) if align and quarter_end else None,
                    "Usable": bool(val is not None), "Reason": reason})
    return out


def _latest(series, i=0):
    if series is None or len(series) <= i:
        return None
    try:
        v = float(series.iloc[i])
        return v if math.isfinite(v) else None
    except (ValueError, TypeError):
        return None


def _interp(x, knots):
    if x <= knots[0][0]:
        return float(knots[0][1])
    if x >= knots[-1][0]:
        return float(knots[-1][1])
    for (x0, y0), (x1, y1) in zip(knots, knots[1:]):
        if x0 <= x <= x1:
            return y0 + (x - x0) / (x1 - x0) * (y1 - y0)
    raise AssertionError("Unexpected interpolation input")


def _growth(frame, annual):
    qr = _values(frame, FIELDS["revenue"])
    if qr is not None and len(qr) >= 5:
        now, prev = _latest(qr), _latest(qr, 4)
        if now is not None and prev and prev > 0:
            return now / prev - 1, "Quarter YoY"
    yr = _values(annual, FIELDS["revenue"])
    if yr is not None and len(yr) >= 2:
        now, prev = _latest(yr), _latest(yr, 1)
        if now is not None and prev and prev > 0:
            return now / prev - 1, "Fiscal year YoY (lagged)"
    return None, "Unavailable"


def _safe_ratio(numerator, denominator):
    return (numerator / denominator if numerator is not None and
            denominator is not None and denominator > 0 else None)


def _info_ratio(info, key):
    value = info.get(key)
    try:
        n = float(value)
        return n if math.isfinite(n) else None
    except (TypeError, ValueError):
        return None


def _equity_to_assets(balance_sheet, quarter_end):
    """Accounting equity / total assets, NOT a regulatory capital adequacy ratio."""
    bal = _frame(balance_sheet)
    if bal.empty or quarter_end is None:
        return None
    aligned = [col for col in bal.columns if col.date() == quarter_end]
    if not aligned:
        return None
    equity = _values(bal, ("Stockholders Equity", "Total Equity Gross Minority Interest",
                           "Common Stock Equity", "Total Equity"))
    assets = _values(bal, ("Total Assets",))
    if equity is None or assets is None:
        return None
    try:
        e = float(equity.loc[aligned[0]])
        a = float(assets.loc[aligned[0]])
        return e / a if math.isfinite(e) and math.isfinite(a) and a > 0 else None
    except (ValueError, TypeError, KeyError):
        return None


def summarize_yahoo(ticker, income, cashflow, annual_income, info=None, today=None,
                    balance_sheet=None):
    """Audit-friendly Yahoo-only research; never an actionable trading recommendation.

    Scores are preliminary, with explicit freshness flags. Yahoo quarter end does
    NOT establish publication date, and bank Yahoo ratios may use rolling periods.
    """
    today = today or date.today()
    ticker = ticker.upper()
    inc, cf, annual = (_frame(x) for x in (income, cashflow, annual_income))
    info = info if isinstance(info, dict) else {}
    quarter_end, latest_reported, selection_reason = _choose_income_quarter(inc, cf)
    age = (today - quarter_end).days if quarter_end else None
    is_bank = ticker in BANK_TICKERS
    rev = _period_value(inc, FIELDS["revenue"], quarter_end)
    operating = _period_value(inc, FIELDS["operating_income"], quarter_end)
    net = _period_value(inc, FIELDS["net_income"], quarter_end)
    cfo = _period_value(cf, FIELDS["operating_cashflow"], quarter_end)
    capex = _period_value(cf, FIELDS["capex"], quarter_end)
    growth, growth_basis = _growth_for_quarter(inc, annual, quarter_end)
    operating_margin = _safe_ratio(operating, rev)
    net_margin = _safe_ratio(net, rev)
    fcf = cfo - abs(capex) if cfo is not None and capex is not None else None
    fcf_margin = _safe_ratio(fcf, rev)

    if is_bank:
        # ROE and ROA are Yahoo snapshot metrics (generally trailing), and need
        # not correspond to the latest income-statement quarter.
        indicators = {
            "Revenue growth": growth,
            "ROE": _info_ratio(info, "returnOnEquity"),
            "ROA": _info_ratio(info, "returnOnAssets"),
            "Equity/assets": _equity_to_assets(balance_sheet, quarter_end),
        }
        weights, scales, model = BANK_WEIGHTS, BANK_SCALES, BANK_MODEL_VERSION
    else:
        indicators = {
            "Revenue growth": growth, "Operating margin": operating_margin,
            "Net margin": net_margin, "FCF margin": fcf_margin,
        }
        weights, scales, model = WEIGHTS, SCALES, QUALITY_MODEL_VERSION

    coverage = sum(weights[k] for k, v in indicators.items() if v is not None)
    components = {k: round(_interp(v, scales[k]), 1) if v is not None else None
                  for k, v in indicators.items()}
    freshness = ("Unknown" if age is None else
                 "Future quarter — check source" if age < -14 else
                 "Expired snapshot" if age > FRESHNESS_HARD_STOP_DAYS else
                 "Potentially stale" if age > FRESHNESS_WARN_DAYS else
                 "Within heuristic age limit")
    if quarter_end is None:
        status = "No quarterly statement"
    elif age is not None and age < -14:
        status = "Future-dated quarter — verify"
    elif age is not None and age > FRESHNESS_HARD_STOP_DAYS:
        status = "Financial data too old"
    elif growth is None:
        status = "Missing growth comparator"
    elif coverage < 75:
        status = "Insufficient bank coverage" if is_bank else "Insufficient field coverage"
    elif is_bank and indicators["ROE"] is None:
        status = "Missing bank ROE"
    elif age is not None and age > FRESHNESS_WARN_DAYS:
        status = "PROVISIONAL — potentially stale"
    else:
        status = "PROVISIONAL — unvalidated"

    score = (round(sum(v for v in components.values() if v is not None), 1)
             if status.startswith("PROVISIONAL") else None)
    valuation = {}
    for k, label in (("forwardPE", "Forward P/E"), ("trailingPE", "Trailing P/E"),
                     ("enterpriseToRevenue", "EV / Revenue"),
                     ("priceToSalesTrailing12Months", "P / Sales")):
        n = _info_ratio(info, k)
        valuation[label] = round(n, 2) if n is not None and n > 0 else None

    details = {
        "Revenue growth %": growth, "Operating margin %": operating_margin,
        "Net margin %": net_margin, "FCF margin %": fcf_margin,
    }
    if is_bank:
        details = {"Revenue growth %": growth, "ROE %": indicators["ROE"],
                   "ROA %": indicators["ROA"],
                   "Equity/assets %": indicators["Equity/assets"]}
    result = {
        "Ticker": ticker, "Business model": ("Bank/lending hybrid" if ticker in SPECIAL_FINANCIAL_TICKERS else "Bank") if is_bank else "Non-bank",
        "Status": status, "Quality / 100": score,
        "Quality model": model, "Latest quarter": str(quarter_end) if quarter_end else None,
        "Latest Yahoo income column": str(latest_reported) if latest_reported else None,
        "Quarter selection": selection_reason,
        "Quarter fallback": bool(quarter_end and latest_reported and quarter_end != latest_reported),
        "Quarter age days": age, "Freshness": freshness, "Coverage %": coverage,
        "Growth basis": growth_basis, "Components": components,
        "Valuation": valuation, "Decision-ready": False,
        "Missing metrics": ", ".join(k for k, v in indicators.items() if v is None) or "None",
        "Source audit": _source_audit(inc, cf, annual, quarter_end),
        "Raw Yahoo rows": {"Income": list(map(str, inc.index)),
                           "Cash flow": list(map(str, cf.index)),
                           "Annual income": list(map(str, annual.index))},
        "Notes": ("Bank score excludes loan loss, NPL, funding, and regulatory capital quality. "
                  "Equity/assets is NOT capital adequacy. ROE/ROA are Yahoo rolling snapshot metrics. "
                  "SOFI is a hybrid bank/lender; the same four high-level bank metrics are provisional and omit credit quality. This is not suitable for trade signals."
                  if is_bank else
                  "Yahoo financial statements may be lagged. Quarterly FCF inputs can use YTD "
                  "reporting; verify accounting periods before trading."),
    }
    for label, v in details.items():
        result[label] = round(v * 100, 2) if v is not None else None
    return result
