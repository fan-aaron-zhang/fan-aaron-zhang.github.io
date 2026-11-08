"""Read-only, on-demand financial source diagnostics. NO fundamental scoring.

SEC XBRL values are not assumed comparable across GAAP/IFRS filers; in
particular a cash-flow statement may contain YTD rather than discrete quarters.
"""
from __future__ import annotations
from datetime import date
import re
from typing import Any
import requests

TEST_TICKERS = ("FN", "AMBA", "DDOG", "TMDX", "NU")
SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"

# Diagnostic tags are candidate matches, not a universal accounting schema.
CANDIDATES = {
    "Revenue": (
        ("us-gaap", "RevenueFromContractWithCustomerExcludingAssessedTax"),
        ("us-gaap", "Revenues"),
        ("us-gaap", "SalesRevenueNet"),
        ("ifrs-full", "Revenue"),
        ("ifrs-full", "RevenueFromContractsWithCustomers"),
        ("ifrs-full", "InterestRevenueCalculatedUsingEffectiveInterestMethod"),
    ),
    "Net income": (
        ("us-gaap", "NetIncomeLoss"),
        ("ifrs-full", "ProfitLoss"),
        ("ifrs-full", "ProfitLossAttributableToOwnersOfParent"),
    ),
    "Operating cash flow": (
        ("us-gaap", "NetCashProvidedByUsedInOperatingActivities"),
        ("ifrs-full", "CashFlowsFromUsedInOperatingActivities"),
    ),
    "Capital expenditure": (
        ("us-gaap", "PaymentsToAcquirePropertyPlantAndEquipment"),
        ("ifrs-full", "PurchaseOfPropertyPlantAndEquipment"),
    ),
}


def sec_headers(contact: str) -> dict[str, str]:
    """SEC asks API users to identify their application and contact address."""
    contact = contact.strip()
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", contact):
        raise ValueError("Provide a valid contact email for the SEC User-Agent (not saved).")
    return {"User-Agent": f"SwingQuantResearch/1.0 research-contact {contact}",
            "Accept-Encoding": "gzip, deflate", "Accept": "application/json"}


def _json(url: str, headers: dict[str, str], get=requests.get) -> Any:
    response = get(url, headers=headers, timeout=15)
    response.raise_for_status()
    return response.json()


def cik_index(payload: dict[str, Any]) -> dict[str, int]:
    entries = payload.values() if isinstance(payload, dict) else payload
    return {str(row["ticker"]).upper(): int(row["cik_str"])
            for row in entries if isinstance(row, dict) and "ticker" in row and "cik_str" in row}


def most_recent_filing(fact: dict[str, Any]) -> tuple[str | None, int]:
    """Latest reported date for available monetary observations, not a validated KPI."""
    observations = []
    for unit, values in fact.get("units", {}).items():
        if unit not in {"USD", "EUR", "GBP"}:
            continue
        for item in values:
            if (item.get("filed") and item.get("end") and
                    item.get("form") in {"10-K", "10-Q", "20-F", "6-K", "40-F"}):
                observations.append(item)
    if not observations:
        return None, 0
    return max(o["filed"] for o in observations), len(observations)


def sec_coverage(companyfacts: dict[str, Any]) -> list[dict[str, Any]]:
    facts = companyfacts.get("facts") or {}
    output = []
    for label, candidates in CANDIDATES.items():
        matches = []
        for taxonomy, name in candidates:
            fact = facts.get(taxonomy, {}).get(name)
            if fact:
                filed, n = most_recent_filing(fact)
                if filed:
                    matches.append((filed, taxonomy, name, n))
        if matches:
            filed, taxonomy, name, n = max(matches)
            output.append({"Metric": label, "Availability": "Present", "Tag": f"{taxonomy}:{name}",
                           "Last filed": filed, "Reported observations": n})
        else:
            output.append({"Metric": label, "Availability": "Not found", "Tag": None,
                           "Last filed": None, "Reported observations": 0})
    return output


def check_sec(ticker: str, headers: dict[str, str], cik_map: dict[str, int], get=requests.get) -> dict[str, Any]:
    cik = cik_map.get(ticker.upper())
    if cik is None:
        return {"Ticker": ticker, "Source": "SEC", "Status": "Ticker not found", "CIK": None,
                "Metrics present": 0, "Metrics checked": len(CANDIDATES), "Latest filing": None,
                "Details": [], "Error": "Ticker absent from SEC company_tickers.json"}
    try:
        facts = _json(SEC_FACTS_URL.format(cik=cik), headers, get)
        details = sec_coverage(facts)
        dates = [x["Last filed"] for x in details if x["Last filed"]]
        found = sum(x["Availability"] == "Present" for x in details)
        return {"Ticker": ticker, "Source": "SEC", "Status": "Available" if found else "No mapped tags",
                "CIK": str(cik), "Metrics present": found, "Metrics checked": len(details),
                "Latest filing": max(dates) if dates else None, "Details": details, "Error": None}
    except Exception as exc:
        return {"Ticker": ticker, "Source": "SEC", "Status": "Request failed", "CIK": str(cik),
                "Metrics present": 0, "Metrics checked": len(CANDIDATES), "Latest filing": None,
                "Details": [], "Error": f"{type(exc).__name__}: {str(exc)[:160]}"}


def check_yahoo(ticker: str, ticker_factory=None) -> dict[str, Any]:
    if ticker_factory is None:
        import yfinance as yf
        ticker_factory = yf.Ticker
    detail = []
    for label, attr in (("Income statement", "quarterly_income_stmt"),
                        ("Cash flow", "quarterly_cashflow"),
                        ("Balance sheet", "quarterly_balance_sheet")):
        try:
            frame = getattr(ticker_factory(ticker), attr)
            cols = len(frame.columns) if frame is not None else 0
            rows = len(frame.index) if frame is not None else 0
            latest = max(str(c.date() if hasattr(c, "date") else c)[:10] for c in frame.columns) if cols else None
            detail.append({"Statement": label, "Available": "Yes" if rows and cols else "Empty",
                           "Rows": rows, "Periods": cols, "Newest period end": latest, "Error": None})
        except Exception as exc:
            detail.append({"Statement": label, "Available": "Error", "Rows": 0, "Periods": 0,
                           "Newest period end": None, "Error": f"{type(exc).__name__}: {str(exc)[:160]}"})
    ok = sum(d["Available"] == "Yes" for d in detail)
    return {"Ticker": ticker, "Source": "Yahoo", "Status": "Available" if ok == 3 else "Partial" if ok else "Unavailable",
            "Statements present": ok, "Statements checked": 3,
            "Latest period end": max((d["Newest period end"] for d in detail if d["Newest period end"]), default=None),
            "Details": detail}


def load_sec_ciks(headers: dict[str, str], get=requests.get) -> dict[str, int]:
    return cik_index(_json(SEC_TICKERS_URL, headers, get))
