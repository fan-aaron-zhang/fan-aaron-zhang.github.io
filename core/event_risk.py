"""Yahoo indicative earnings watch: upcoming AND recent events.

A Yahoo date alone does not prove a company reported. An actual Reported EPS
value supplies stronger (still third-party) evidence for a recent event.
Missing data is always Unknown, never Clear. No trade instruction is implied.
"""
from __future__ import annotations
from datetime import date, datetime
import pandas as pd

EVENT_MODEL = "E0.2-recent-earnings"


def _dates_from(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return [d for x in value for d in _dates_from(x)]
    if isinstance(value, (pd.DataFrame, pd.Series)):
        return []
    if isinstance(value, (date, datetime, pd.Timestamp)):
        return [value.date() if isinstance(value, (datetime, pd.Timestamp)) else value]
    if isinstance(value, str):
        try:
            t = pd.to_datetime(value, errors="coerce")
            if pd.notna(t):
                return [t.date()]
        except (TypeError, ValueError, OverflowError):
            pass
    return []


def parse_earnings_calendar(calendar) -> list[date]:
    if not isinstance(calendar, dict):
        return []
    for key, val in calendar.items():
        if str(key).lower().replace("_", " ").strip() in {"earnings date", "earnings dates"}:
            return sorted(set(_dates_from(val)))
    return []


def parse_earnings_history(history) -> list[dict]:
    """Parse Yahoo earnings_dates rows without treating a scheduled past date as confirmed."""
    if not isinstance(history, pd.DataFrame) or history.empty:
        return []
    records = []
    for idx, row in history.iterrows():
        dates = _dates_from(idx)
        if not dates:
            continue
        actual = None
        for name in row.index:
            if str(name).lower().replace("_", " ").strip() in {"reported eps", "eps actual", "actual eps"}:
                actual = pd.to_numeric(row[name], errors="coerce")
                break
        records.append({"date": dates[0], "actual_reported": actual is not None and pd.notna(actual)})
    return records


def assess_earnings_risk(ticker: str, calendar, today: date | None = None,
                         near_days: int = 7, watch_days: int = 14,
                         earnings_history=None, recent_days: int = 7) -> dict:
    today = today or date.today()
    calendar_dates = parse_earnings_calendar(calendar)
    history = parse_earnings_history(earnings_history)
    upcoming = sorted(set(d for d in calendar_dates if d >= today) |
                      {r["date"] for r in history if r["date"] >= today})
    past = {}
    for d in calendar_dates:
        if d <= today:
            past[d] = False
    for r in history:
        if r["date"] <= today:
            past[r["date"]] = past.get(r["date"], False) or r["actual_reported"]
    recent = [(d, confirmed) for d, confirmed in past.items()
              if 0 <= (today - d).days <= recent_days]
    recent.sort(key=lambda pair: (pair[0], pair[1]), reverse=True)
    future = upcoming[0] if upcoming else None
    next_days = (future - today).days if future else None
    base = {
        "ticker": ticker, "model": EVENT_MODEL,
        "source": "Yahoo Finance calendar and earnings_dates (indicative)",
        "checked_on": str(today), "earnings_date": str(future) if future else None,
        "days_until": next_days, "last_event_date": None, "days_since": None,
        "recent_confirmed_eps": None,
        "note": "Yahoo dates may be estimated; check company IR for significant trades.",
    }
    if recent:
        d, confirmed = recent[0]
        label = "Recent (reported EPS)" if confirmed else "Recent (date unverified)"
        return {**base, "last_event_date": str(d), "days_since": (today-d).days,
                "recent_confirmed_eps": confirmed, "status": label,
                "risk": "Post-earnings watch",
                "reason": ("Yahoo shows reported EPS for a recent event; company IR still authoritative"
                           if confirmed else "Recent Yahoo date found, but actual publication not verified")}
    if future is None:
        return {**base, "status": "Unknown", "risk": "Unassessed",
                "reason": "No identifiable recent or future Yahoo earnings date"}
    if next_days <= near_days:
        status, risk = "Within 7 days", "Event near"
    elif next_days <= watch_days:
        status, risk = "Within 14 days", "Calendar watch"
    else:
        status, risk = "Later", "No near earnings in calendar"
    return {**base, "status": status, "risk": risk,
            "reason": "Estimated event proximity, not a prediction of earnings reaction"}
